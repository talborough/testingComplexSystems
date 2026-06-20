#!/usr/bin/python3
#
# gDSSchema.py - gDS schema IR helpers, verification, and schema loading for gDSCompile.
#
# IR storage (dsTable / dsVariable) lives in gDSIr.py.
#

import inspect
import os
import sys

from gDSIr import *

Cli = None


def _verify_codegen_mirror_is_plain():
    """``gDSIr.py`` must use plain lists; the compile stack never uses ``Manager``."""
    if type(dsTable_Name).__name__ == "list":
        return
    raise RuntimeError(
        "gDSIr.py is trying to use multiprocessing Manager storage, which is not allowed; "
        "rebuild gDSIr.py using 'gDSCompile -O gDSIr.dd'"
    )


_BARE_COLUMN_VARIABLE_TYPES = frozenset(
    {"defineColumn", "defineName", "defineRowStatus"}
)

def _announce_step(step_kind, step_id, message):
    """Print a Phase/verify/generate step label when ``-v`` verbose is enabled."""
    cli = Cli
    if cli is None or not getattr(cli, "verbose", False):
        return
    kind = step_kind.lower()
    if kind == "verify":
        print(f"  Verify {step_id}: {message}")
    elif kind == "generate":
        print(f"  Generate {step_id}: {message}")
    elif kind == "phase":
        print(f"Phase {step_id}: {message}")
    else:
        print(f"{step_kind} {step_id}: {message}")






def _ordinary_containers():
    """True when ``-O`` applies to the generated *target* ``.py`` (not this executable)."""
    cli = Cli
    return cli is not None and getattr(cli, "ordinary_containers", False)


def _parse_list():
    """Empty list for many-ref wiring while parsing (codegen mirror is always plain)."""
    return []






# 0-based field column index on a trimmed schema line: parts[0] is column 0, parts[1] is 1, …
_KW_FIELD_COL = 0
_NAME_FIELD_COL = 1


# Verify A — only these keywords allowed between defineTable and endTable (see module doc).
_INNER_SCHEMA_KEYWORDS = frozenset(
    {
        "defineColumn",
        "defineIndexOneRef",
        "defineIndexManyRefs",
        "defineOneRef",
        "defineManyRefs",
        "defineName",
        "defineRowStatus",
    }
)

# Values stored in ``dsTable_Type`` (``columnar`` from ``defineTable``; ``unary`` / ``list`` / ``dict`` from shorthands).
_DS_TABLE_TYPE_UNARY = "unary"
_DS_TABLE_TYPE_LIST = "list"
_DS_TABLE_TYPE_DICT = "dict"
_DS_TABLE_TYPE_COLUMNAR = "columnar"

# ``dsVariable_Type`` equals the singular table-kind token for shorthand-expanded rows.
_DS_VARIABLE_TYPE_FROM_DEFINE_UNARY = _DS_TABLE_TYPE_UNARY
_DS_VARIABLE_TYPE_FROM_DEFINE_LIST = _DS_TABLE_TYPE_LIST
_DS_VARIABLE_TYPE_FROM_DEFINE_DICT = _DS_TABLE_TYPE_DICT

# (keyword → ``dsTable_Type``, ``dsVariable_Type``).
_TOP_LEVEL_SINGULAR_ROW_SPECS = {
    "defineUnary": (_DS_TABLE_TYPE_UNARY, _DS_VARIABLE_TYPE_FROM_DEFINE_UNARY),
    "defineList": (_DS_TABLE_TYPE_LIST, _DS_VARIABLE_TYPE_FROM_DEFINE_LIST),
    "defineDict": (_DS_TABLE_TYPE_DICT, _DS_VARIABLE_TYPE_FROM_DEFINE_DICT),
}

# Top-level directives other than ``defineTable`` … (Verify A).
_TOP_LEVEL_SCHEMA_KEYWORDS = frozenset(_TOP_LEVEL_SINGULAR_ROW_SPECS.keys())

# ``dsVariable_Type`` values that create shared storage (columnar inner lines).
_LIST_EMITTING_VARIABLE_TYPES = frozenset(
    {
        "defineColumn",
        "defineOneRef",
        "defineManyRefs",
        "defineRowStatus",
    }
)
_INDEX_ONE_REF_TYPE = "defineIndexOneRef"
_INDEX_MANY_REFS_TYPE = "defineIndexManyRefs"
_INDEX_ONE_SUFFIX = "_2Ref"
_INDEX_MANY_SUFFIX = "_2Refs"
_INDEX_VARIABLE_TYPES = frozenset({_INDEX_ONE_REF_TYPE, _INDEX_MANY_REFS_TYPE})

_DICT_EMITTING_VARIABLE_TYPES = _INDEX_VARIABLE_TYPES

# ``dsVariable_Type`` values that become ``<table>_AddARow`` parameters (not index types).
_ADDAROW_PARAMETER_TYPES = _LIST_EMITTING_VARIABLE_TYPES | frozenset({"defineName"})

# ``defineOneRef``: optional value 1 = referenced table; optional value 2 = AddARow default.
# ``defineManyRefs``: optional value 1 = referenced table only (no AddARow default).
_REF_VARIABLE_TYPES = frozenset({"defineOneRef", "defineManyRefs"})
_OPTIONAL_VALUE1_REQUIRED_TYPES = frozenset(
    {_INDEX_ONE_REF_TYPE, _INDEX_MANY_REFS_TYPE, "defineOneRef", "defineManyRefs"}
)
_OPTIONAL_VALUE1_REQUIRED_MSG = {
    _INDEX_ONE_REF_TYPE: "the key column (column to index) as optional value 1",
    _INDEX_MANY_REFS_TYPE: "the key column (column to index) as optional value 1",
    "defineOneRef": "the referenced table name as optional value 1",
    "defineManyRefs": "the referenced table name as optional value 1",
}
# Only these two tables after parse => gDSIr.dd schema (see file header).
_GDSCODEGEN_PROCESSOR_TABLE_NAMES = frozenset({"dsTable", "dsVariable"})
_ONE_REF_VARIABLE_TYPES = frozenset({"defineOneRef"})


def _optional_tokens_after_name(parts):
    """Map ``parts[2:]`` into optional-value fields (at most three stored)."""
    extras = len(parts) - 2
    if extras <= 0:
        return (0, None, None, None)
    n = min(extras, 3)
    opt1 = parts[2] if extras >= 1 else None
    opt2 = parts[3] if extras >= 2 else None
    opt3 = parts[4] if extras >= 3 else None
    return (n, opt1, opt2, opt3)


def _parse_error(schema_path, schema_line_no, message):
    """Caller line in ``gDSSchema``; schema path and .dd line (or ``<None>``) for every error."""
    driver_line = inspect.currentframe().f_back.f_lineno
    dd_line = schema_line_no if schema_line_no is not None else "<None>"
    return f"gDSSchema:{driver_line}: {schema_path}:{dd_line}: {message}"


def parseSchemaFileToTables():
    """Load the CLI ``.dd`` into gDS mirrors: ``dsTable`` / ``dsVariable``.

    While loading, **Verify A–E** from the module doc run: legal keywords, correct nesting of
    ``defineTable`` / ``endTable`` and singular lines, no duplicate variable (or table) names,
    exactly one ``defineRowStatus`` per columnar table as the last inner directive before ``endTable``,
    and exactly one ``defineName`` per columnar table. **Verify F** runs after load (optional value 1
    for ``defineIndexOneRef``, ``defineIndexManyRefs``, ``defineOneRef``, and ``defineManyRefs``).

    ``dsVariable_LineIndex`` is the **0-based ordinal** of the variable definition within its
    ``defineTable`` … ``endTable`` block (first definition → ``0``, second → ``1``, …).

    ``dsTable_DefineLineIndex`` / ``dsTable_EndLineIndex`` remain **0-based token positions**
    on the ``defineTable`` / ``endTable`` schema lines (keyword → ``0``, table name → ``1`` on
    ``defineTable`` lines).

    ``defineTable`` blocks are always columnar. Singular shorthands (``defineUnary`` / ``defineList`` /
    ``defineDict``) emit non-columnar ``dsTable`` rows and never open an inner block.
    """
    cli = Cli
    if cli is None:
        raise RuntimeError(
            _parse_error("<no schema path>", None, "parseSchemaFileToTables called before Cli is set")
        )

    dd_filepath = _schema_file_path(cli)

    _announce_step("Phase", 1, f"load schema file {dd_filepath!r} into tables (make checks below)")
    _announce_step("verify", "A", "all keywords are legal")
    _announce_step(
        "verify",
        "B",
        "begin/inner/end and singular constructs are nested correctly",
    )
    _announce_step("verify", "C", "no duplicate variable names")
    _announce_step(
        "verify",
        "D",
        "one defineRowStatus per table; must be last before endTable",
    )
    _announce_step("verify", "E", "one defineName per table")
    _announce_step(
        "verify",
        "F",
        "defineIndexOneRef, defineOneRef, and defineManyRefs each cite optional value 1",
    )
    _announce_step(
        "verify",
        "G",
        "defineManyRefs must not specify optional value 2",
    )

    inside_table = False
    current_ds_table_row = None
    current_table_variable_refs = None
    table_column_def_index = 0
    row_status_seen = False
    name_directive_seen = False

    try:
        fh = open(dd_filepath, encoding="utf-8", newline="")
    except OSError as exc:
        raise OSError(
            _parse_error(dd_filepath, None, f"cannot open schema file ({exc})")
        ) from exc

    with fh:
        for schema_line_no, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            if "#" in line:
                line = line.split("#", 1)[0].strip()
            if not line:
                continue

            parts = line.split()
            kw = parts[0]
            if kw == "defineTable":
                if inside_table:
                    raise ValueError(
                        _parse_error(
                            dd_filepath,
                            schema_line_no,
                            "(Verify B) nested defineTable before endTable",
                        )
                    )
                if len(parts) < 2:
                    raise ValueError(
                        _parse_error(
                            dd_filepath,
                            schema_line_no,
                            "(Verify B) defineTable missing table name",
                        )
                    )
                tbl_name = parts[1]
                inside_table = True
                table_column_def_index = 0
                row_status_seen = False
                name_directive_seen = False
                current_table_variable_refs = _parse_list()
                current_ds_table_row = dsTable_AddARow(
                    _dsTable_Name=tbl_name,
                    _dsTable_dsVariable_Refs=current_table_variable_refs,
                    _dsTable_Type=_DS_TABLE_TYPE_COLUMNAR,
                    _dsTable_DefineLineNumber=schema_line_no,
                    _dsTable_DefineLineIndex=_NAME_FIELD_COL,
                    _dsTable_EndLineNumber=None,
                    _dsTable_EndLineIndex=None,
                    _dsTable_RowStatus="parse",
                )
                continue

            if kw == "endTable":
                if not inside_table or current_ds_table_row is None:
                    raise ValueError(
                        _parse_error(
                            dd_filepath,
                            schema_line_no,
                            "(Verify B) endTable outside of defineTable block",
                        )
                    )
                if not name_directive_seen:
                    raise ValueError(
                        _parse_error(
                            dd_filepath,
                            schema_line_no,
                            "(Verify E) each table must have exactly one defineName "
                            "(Name column)",
                        )
                    )
                if not row_status_seen:
                    raise ValueError(
                        _parse_error(
                            dd_filepath,
                            schema_line_no,
                            "(Verify D) each table must have exactly one defineRowStatus "
                            "(RowStatus column), last before endTable",
                        )
                    )
                dsTable_EndLineNumber[current_ds_table_row] = schema_line_no
                dsTable_EndLineIndex[current_ds_table_row] = _KW_FIELD_COL
                inside_table = False
                current_ds_table_row = None
                current_table_variable_refs = None
                row_status_seen = False
                name_directive_seen = False
                continue

            if kw in _TOP_LEVEL_SINGULAR_ROW_SPECS:
                if inside_table:
                    raise ValueError(
                        _parse_error(
                            dd_filepath,
                            schema_line_no,
                            f"(Verify B) {kw!r} is not allowed inside a defineTable … endTable block",
                        )
                    )
                if len(parts) < 2:
                    raise ValueError(
                        _parse_error(
                            dd_filepath,
                            schema_line_no,
                            f"(Verify B) {kw!r} missing variable name",
                        )
                    )
                tbl_t, col_t = _TOP_LEVEL_SINGULAR_ROW_SPECS[kw]
                u_name = parts[1]
                optional_value_count, opt1, opt2, opt3 = _optional_tokens_after_name(parts)
                if kw == "defineUnary" and optional_value_count < 1:
                    raise ValueError(
                        _parse_error(
                            dd_filepath,
                            schema_line_no,
                            f"(Verify B) {kw!r} {u_name!r} requires the initial value "
                            "as the first optional value",
                        )
                    )
                try:
                    singular_variable_refs = _parse_list()
                    tref = dsTable_AddARow(
                        _dsTable_Name=u_name,
                        _dsTable_dsVariable_Refs=singular_variable_refs,
                        _dsTable_Type=tbl_t,
                        _dsTable_DefineLineNumber=schema_line_no,
                        _dsTable_DefineLineIndex=_NAME_FIELD_COL,
                        _dsTable_EndLineNumber=schema_line_no,
                        _dsTable_EndLineIndex=_NAME_FIELD_COL,
                        _dsTable_RowStatus="parse",
                    )
                    vref = dsVariable_AddARow(
                        _dsVariable_Name=u_name,
                        _dsVariable_Type=col_t,
                        _dsVariable_OptionalValueCount=optional_value_count,
                        _dsVariable_OptionalValue1=opt1,
                        _dsVariable_OptionalValue2=opt2,
                        _dsVariable_OptionalValue3=opt3,
                        _dsVariable_LineNumber=schema_line_no,
                        _dsVariable_LineIndex=0,
                        _dsVariable_dsTable_Ref=tref,
                        _dsVariable_BareName=_bare_name_for_schema_variable(col_t, u_name),
                        _dsVariable_RowStatus="parse",
                    )
                    singular_variable_refs.append(vref)
                except KeyError as exc:
                    raise ValueError(
                        _parse_error(
                            dd_filepath,
                            schema_line_no,
                            f"(Verify C) duplicate table or variable name ({exc})",
                        )
                    ) from exc
                continue

            if not inside_table or current_ds_table_row is None:
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        schema_line_no,
                        f"(Verify A) unknown or top-level directive {kw!r} "
                        f"(expected defineTable … or {sorted(_TOP_LEVEL_SCHEMA_KEYWORDS)!r})",
                    )
                )

            if kw not in _INNER_SCHEMA_KEYWORDS:
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        schema_line_no,
                        f"(Verify A) illegal keyword {kw!r}",
                    )
                )

            if len(parts) < 2:
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        schema_line_no,
                        f"(Verify B) {kw!r} missing variable name",
                    )
                )
            var_name = parts[1]
            if kw == "defineName" and name_directive_seen:
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        schema_line_no,
                        "(Verify E) exactly one defineName per table (Name column)",
                    )
                )
            if row_status_seen:
                if kw == "defineRowStatus":
                    raise ValueError(
                        _parse_error(
                            dd_filepath,
                            schema_line_no,
                            "(Verify D) exactly one defineRowStatus per table (RowStatus must be last)",
                        )
                    )
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        schema_line_no,
                        "(Verify D) defineRowStatus must be the last inner directive "
                        "before endTable (nothing after RowStatus)",
                    )
                )
            optional_value_count, opt1, opt2, opt3 = _optional_tokens_after_name(parts)

            try:
                vref = dsVariable_AddARow(
                    _dsVariable_Name=var_name,
                    _dsVariable_Type=kw,
                    _dsVariable_OptionalValueCount=optional_value_count,
                    _dsVariable_OptionalValue1=opt1,
                    _dsVariable_OptionalValue2=opt2,
                    _dsVariable_OptionalValue3=opt3,
                    _dsVariable_LineNumber=schema_line_no,
                    _dsVariable_LineIndex=table_column_def_index,
                    _dsVariable_dsTable_Ref=current_ds_table_row,
                    _dsVariable_BareName=_bare_name_for_schema_variable(kw, var_name),
                    _dsVariable_RowStatus="parse",
                )
                current_table_variable_refs.append(vref)
                table_column_def_index += 1
                if kw == "defineName":
                    name_directive_seen = True
                if kw == "defineRowStatus":
                    row_status_seen = True
            except KeyError as exc:
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        schema_line_no,
                        f"(Verify C) duplicate variable name ({exc})",
                    )
                ) from exc

    if inside_table:
        raise ValueError(
            _parse_error(dd_filepath, None, "(Verify B) missing endTable before end of file")
        )

    verify_schema_phase_1_f(dd_filepath)
    verify_schema_phase_1_g(dd_filepath)
    verify_schema_phase_2(dd_filepath)
    verify_schema_phase_3_native_naming(dd_filepath)
    apply_processor_schema_O_mode(dd_filepath)
    return


def _dump_loaded_schema_tables():
    """Print ``dsTable`` and ``dsVariable`` mirrors (``-d``), after load and before codegen."""
    cli = Cli
    if cli is None or not getattr(cli, "dump", False):
        return
    _announce_step(
        "Phase",
        "dump",
        "dsTable and dsVariable after schema load (before code generation)",
    )
    dsTable_DumpRows()
    dsVariable_DumpRows()


def _is_gdscodegen_processor_schema():
    """True when we are processing the gDSIr.dd processor schema.

    After the first parse, if only ``dsTable`` and ``dsVariable`` exist, we assume this
    .dd file describes the code generator itself (not an application schema).
    """
    if len(dsTable_Name) != 2:
        return False
    return {dsTable_Name[tref] for tref in range(len(dsTable_Name))} == _GDSCODEGEN_PROCESSOR_TABLE_NAMES


def _processor_schema_intro(dd_filepath):
    """Short identification line for the gDSIr.dd processor schema (``dsTable`` + ``dsVariable`` only)."""
    dd_name = os.path.basename(dd_filepath)
    return (
        f"Processor schema {dd_name!r} (only dsTable and dsVariable — "
        "the code generator's own mirror, not an application schema)"
    )


def _columnar_table_names():
    """Set of table names for columnar (``defineTable``) rows in the loaded schema."""
    return {
        dsTable_Name[tref]
        for tref in range(len(dsTable_Name))
        if dsTable_Type[tref] == _DS_TABLE_TYPE_COLUMNAR
    }


def _bare_name_for_schema_variable(vtype, var_name):
    """Bare column name (rhs of first ``_``) for column-bearing variables; else ``None``."""
    if vtype not in _BARE_COLUMN_VARIABLE_TYPES:
        return None
    _table_part, column_part = var_name.split("_", 1)
    return column_part


def _ref_table_implied_by_column_name(owning_table, var_name, vtype):
    """Referenced table encoded in ``<owning>_<referenced>_<Ref|Refs>``, or ``None``."""
    prefix = f"{owning_table}_"
    if not var_name.startswith(prefix):
        return None
    tail = var_name[len(prefix) :]
    if vtype == "defineOneRef":
        if not tail.endswith("_Ref"):
            return None
        return tail[: -len("_Ref")]
    if vtype == "defineManyRefs":
        if not tail.endswith("_Refs"):
            return None
        return tail[: -len("_Refs")]
    return None


def _index_one_ref_implied_column(owning_table, index_var):
    """Column name implied by ``{table}_{tail}_2Ref`` index naming, or ``None`` if malformed."""
    if "_" not in index_var:
        return None
    lhs, rhs = index_var.split("_", 1)
    if lhs != owning_table or not rhs.endswith(_INDEX_ONE_SUFFIX):
        return None
    column_tail = rhs[: -len(_INDEX_ONE_SUFFIX)]
    if not column_tail:
        return None
    return f"{owning_table}_{column_tail}"


def _index_many_refs_implied_column(owning_table, index_var):
    """Column name implied by ``{table}_{tail}_2Refs`` index naming, or ``None`` if malformed."""
    if "_" not in index_var:
        return None
    lhs, rhs = index_var.split("_", 1)
    if lhs != owning_table or not rhs.endswith(_INDEX_MANY_SUFFIX):
        return None
    column_tail = rhs[: -len(_INDEX_MANY_SUFFIX)]
    if not column_tail:
        return None
    return f"{owning_table}_{column_tail}"


def verify_schema_phase_3_native_naming(dd_filepath):
    """Phase 3 — native gDS naming conventions (shape and ref/index name consistency)."""
    _announce_step("Phase", 3, "verify native gDS naming conventions")
    _announce_step("verify", "A", "table names contain no '_'")
    for tref in range(len(dsTable_Name)):
        if dsTable_Type[tref] != _DS_TABLE_TYPE_COLUMNAR:
            continue
        tbl_name = dsTable_Name[tref]
        if "_" in tbl_name:
            raise ValueError(
                _parse_error(
                    dd_filepath,
                    dsTable_DefineLineNumber[tref],
                    f"(Phase 3 verify A) table name {tbl_name!r} must not contain '_'",
                )
            )
    _announce_step("verify", "B", "every column name starts with '{table}_'")
    for tref in range(len(dsTable_Name)):
        if dsTable_Type[tref] != _DS_TABLE_TYPE_COLUMNAR:
            continue
        tbl_name = dsTable_Name[tref]
        prefix = f"{tbl_name}_"
        for vref in _variable_refs_for_table(tref):
            var_name = dsVariable_Name[vref]
            if not var_name.startswith(prefix):
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        dsVariable_LineNumber[vref],
                        f"(Phase 3 verify B) {var_name!r} must start with {prefix!r} "
                        f"(table {tbl_name!r})",
                    )
                )
    _announce_step(
        "verify",
        "C",
        "defineName ends with '_Name'; defineRowStatus ends with '_RowStatus'",
    )
    for tref in range(len(dsTable_Name)):
        if dsTable_Type[tref] != _DS_TABLE_TYPE_COLUMNAR:
            continue
        for vref in _variable_refs_for_table(tref):
            vtype = dsVariable_Type[vref]
            var_name = dsVariable_Name[vref]
            line_no = dsVariable_LineNumber[vref]
            if vtype == "defineName" and not var_name.endswith("_Name"):
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        line_no,
                        f"(Phase 3 verify C) defineName {var_name!r} must end with '_Name'",
                    )
                )
            if vtype == "defineRowStatus" and not var_name.endswith("_RowStatus"):
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        line_no,
                        f"(Phase 3 verify C) defineRowStatus {var_name!r} must end with '_RowStatus'",
                    )
                )
    _announce_step(
        "verify",
        "D",
        "defineOneRef ends with '_Ref'; defineManyRefs ends with '_Refs'",
    )
    for tref in range(len(dsTable_Name)):
        if dsTable_Type[tref] != _DS_TABLE_TYPE_COLUMNAR:
            continue
        for vref in _variable_refs_for_table(tref):
            vtype = dsVariable_Type[vref]
            var_name = dsVariable_Name[vref]
            line_no = dsVariable_LineNumber[vref]
            if vtype == "defineOneRef" and not var_name.endswith("_Ref"):
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        line_no,
                        f"(Phase 3 verify D) defineOneRef {var_name!r} must end with '_Ref'",
                    )
                )
            if vtype == "defineManyRefs" and not var_name.endswith("_Refs"):
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        line_no,
                        f"(Phase 3 verify D) defineManyRefs {var_name!r} must end with '_Refs'",
                    )
                )
    _announce_step(
        "verify",
        "E",
        "ref column names are '{owning}_{dest}_{Ref|Refs}' with dest not equal to owning",
    )
    for tref in range(len(dsTable_Name)):
        if dsTable_Type[tref] != _DS_TABLE_TYPE_COLUMNAR:
            continue
        owning_table = dsTable_Name[tref]
        for vref in _variable_refs_for_table(tref):
            vtype = dsVariable_Type[vref]
            if vtype not in _REF_VARIABLE_TYPES:
                continue
            var_name = dsVariable_Name[vref]
            line_no = dsVariable_LineNumber[vref]
            parts = var_name.split("_")
            if len(parts) != 3:
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        line_no,
                        f"(Phase 3 verify E) {vtype} {var_name!r} must split into exactly "
                        f"three '_' segments (got {len(parts)})",
                    )
                )
            if parts[1] == owning_table:
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        line_no,
                        f"(Phase 3 verify E) {vtype} {var_name!r} middle segment {parts[1]!r} "
                        f"cannot be the owning table {owning_table!r}",
                    )
                )
    _announce_step(
        "verify",
        "F",
        "ref optional value 1 matches the middle segment of the column name",
    )
    for tref in range(len(dsTable_Name)):
        if dsTable_Type[tref] != _DS_TABLE_TYPE_COLUMNAR:
            continue
        owning_table = dsTable_Name[tref]
        for vref in _variable_refs_for_table(tref):
            vtype = dsVariable_Type[vref]
            if vtype not in _REF_VARIABLE_TYPES:
                continue
            var_name = dsVariable_Name[vref]
            line_no = dsVariable_LineNumber[vref]
            opt1_table = dsVariable_OptionalValue1[vref]
            name_table = _ref_table_implied_by_column_name(
                owning_table, var_name, vtype
            )
            if name_table is None:
                parts = var_name.split("_")
                if len(parts) == 3:
                    name_table = parts[1]
            if name_table is None or name_table == opt1_table:
                continue
            raise ValueError(
                _parse_error(
                    dd_filepath,
                    line_no,
                    f"(Phase 3 verify F) {vtype} {var_name!r} optional value 1 is "
                    f"{opt1_table!r} but the column name implies referenced table "
                    f"{name_table!r}",
                )
            )
    _announce_step(
        "verify",
        "G",
        "defineIndexOneRef is '{table}_{tail}_2Ref' and optional value 1 names that column",
    )
    for tref in range(len(dsTable_Name)):
        if dsTable_Type[tref] != _DS_TABLE_TYPE_COLUMNAR:
            continue
        owning_table = dsTable_Name[tref]
        for vref in _variables_of_type(tref, _INDEX_ONE_REF_TYPE):
            index_var = dsVariable_Name[vref]
            line_no = dsVariable_LineNumber[vref]
            implied_col = _index_one_ref_implied_column(owning_table, index_var)
            if implied_col is None:
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        line_no,
                        f"(Phase 3 verify G) defineIndexOneRef {index_var!r} must be "
                        f"'{owning_table}_<tail>{_INDEX_ONE_SUFFIX}'",
                    )
                )
            key_col = dsVariable_OptionalValue1[vref]
            if key_col != implied_col:
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        line_no,
                        f"(Phase 3 verify G) defineIndexOneRef {index_var!r} implies column "
                        f"{implied_col!r} but optional value 1 is {key_col!r}",
                    )
                )
    _announce_step(
        "verify",
        "H",
        "defineIndexManyRefs is '{table}_{tail}_2Refs' and optional value 1 names that column",
    )
    for tref in range(len(dsTable_Name)):
        if dsTable_Type[tref] != _DS_TABLE_TYPE_COLUMNAR:
            continue
        owning_table = dsTable_Name[tref]
        for vref in _variables_of_type(tref, _INDEX_MANY_REFS_TYPE):
            index_var = dsVariable_Name[vref]
            line_no = dsVariable_LineNumber[vref]
            implied_col = _index_many_refs_implied_column(owning_table, index_var)
            if implied_col is None:
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        line_no,
                        f"(Phase 3 verify H) defineIndexManyRefs {index_var!r} must be "
                        f"'{owning_table}_<tail>{_INDEX_MANY_SUFFIX}'",
                    )
                )
            key_col = dsVariable_OptionalValue1[vref]
            if key_col != implied_col:
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        line_no,
                        f"(Phase 3 verify H) defineIndexManyRefs {index_var!r} implies column "
                        f"{implied_col!r} but optional value 1 is {key_col!r}",
                    )
                )


def apply_processor_schema_O_mode(dd_filepath):
    """Force ``-O`` for generated output when the processor schema (``dsTable`` + ``dsVariable``) is detected."""
    if not _is_gdscodegen_processor_schema():
        return
    cli = Cli
    if cli is None:
        return
    intro = _processor_schema_intro(dd_filepath)
    out_py = os.path.basename(_output_py_path(cli))
    if _ordinary_containers():
        _announce_step(
            "Phase",
            "O",
            f"{intro}. Generated {out_py!r} will use ordinary [] and {{}} "
            "(-O was already specified).",
        )
        return
    cli.ordinary_containers = True
    _announce_step(
        "Phase",
        "O",
        f"{intro}. Enabling -O for this run so {out_py!r} uses ordinary [] and {{}} "
        "(not multiprocessing Manager; so the code generator itself can run anywhere).",
    )


def verify_schema_phase_1_f(dd_filepath):
    """Phase 1 verify F — index/ref types require optional value 1."""
    for vref in range(len(dsVariable_Name)):
        vtype = dsVariable_Type[vref]
        if vtype not in _OPTIONAL_VALUE1_REQUIRED_TYPES:
            continue
        if dsVariable_OptionalValueCount[vref] >= 1 and dsVariable_OptionalValue1[vref]:
            continue
        var_name = dsVariable_Name[vref]
        need = _OPTIONAL_VALUE1_REQUIRED_MSG[vtype]
        raise ValueError(
            _parse_error(
                dd_filepath,
                dsVariable_LineNumber[vref],
                f"(Phase 1 verify F) {vtype} {var_name!r} requires {need}",
            )
        )


def verify_schema_phase_1_g(dd_filepath):
    """Phase 1 verify G — ``defineManyRefs`` must not use optional value 2."""
    for vref in range(len(dsVariable_Name)):
        if dsVariable_Type[vref] != "defineManyRefs":
            continue
        if dsVariable_OptionalValueCount[vref] < 2:
            continue
        var_name = dsVariable_Name[vref]
        raise ValueError(
            _parse_error(
                dd_filepath,
                dsVariable_LineNumber[vref],
                f"(Phase 1 verify G) defineManyRefs {var_name!r} must not specify "
                "optional value 2 (only optional value 1, the referenced table, is allowed)",
            )
        )


def _schema_ref_edges():
    """``(owning_table, dest_table, var_name, line_no, vtype)`` per ref column."""
    edges = []
    for tref in range(len(dsTable_Name)):
        owning_table = dsTable_Name[tref]
        for vref in dsTable_dsVariable_Refs[tref]:
            vtype = dsVariable_Type[vref]
            if vtype not in _REF_VARIABLE_TYPES:
                continue
            edges.append(
                (
                    owning_table,
                    dsVariable_OptionalValue1[vref],
                    dsVariable_Name[vref],
                    dsVariable_LineNumber[vref],
                    vtype,
                )
            )
    return edges


def _schema_ref_graph_from_edges(ref_edges):
    """Owning table -> list of referenced tables (adjacency from *ref_edges*)."""
    schema_graph = {}
    for owning_table, dest_table, _var, _line, _vtype in ref_edges:
        schema_graph.setdefault(owning_table, []).append(dest_table)
        schema_graph.setdefault(dest_table, [])
    return schema_graph


def find_reference_cycle(schema_graph):
    """Return table names on one directed cycle, or ``None`` if the graph is acyclic."""
    color = {}
    parent = {}

    def dfs(node):
        color[node] = 1
        for neighbor in schema_graph.get(node, []):
            if color.get(neighbor) == 1:
                cycle = [neighbor]
                walk = node
                while walk != neighbor:
                    cycle.append(walk)
                    walk = parent[walk]
                cycle.reverse()
                return cycle
            if color.get(neighbor, 0) == 0:
                parent[neighbor] = node
                found = dfs(neighbor)
                if found:
                    return found
        color[node] = 2
        return None

    for start in schema_graph:
        if color.get(start, 0) == 0:
            found = dfs(start)
            if found:
                return found
    return None


def _format_reference_cycle_message(cycle_tables, ref_edges):
    """Multi-line Phase 2 verify D failure: cycle, refs, side-effects, remediation."""
    if cycle_tables[0] != cycle_tables[-1]:
        cycle_display = cycle_tables + [cycle_tables[0]]
    else:
        cycle_display = list(cycle_tables)
    path = " -> ".join(cycle_display)
    ref_lines = []
    for i in range(len(cycle_display) - 1):
        owning, dest = cycle_display[i], cycle_display[i + 1]
        for o, d, var_name, line_no, vtype in ref_edges:
            if o == owning and d == dest:
                ref_lines.append(
                    f"    {o} --{var_name} ({vtype})--> {d}  (.dd line {line_no})"
                )
    if not ref_lines:
        ref_lines.append("    (no defineOneRef/defineManyRefs matched the cycle edges)")
    return "\n".join(
        [
            "(Phase 2 verify D) reference cycle detected among tables",
            f"  Cycle: {path}",
            "  References on this cycle:",
            *ref_lines,
            "  Side-effects of a cycle:",
            "    - DeleteRows / ApplyRAL need a clear order to update referencing tables;",
            "      a cycle has no valid topological order, so updating references is undefined.",
            "    - Generated code may apply RAL updates in an order that never stabilizes.",
            "  To eliminate the cycle:",
            "    - Remove or repoint at least one defineOneRef/defineManyRefs on the cycle",
            "      so the reference graph is acyclic (a directed acyclic graph, or DAG:",
            "      follow refs from owning table to referenced table only; no table may reach itself).",
        ]
    )


def verify_schema_phase_2(dd_filepath):
    """Phase 2 — semantic integrity (refs, indexes, reference graph)."""
    _announce_step("Phase", 2, "semantic integrity")
    columnar_tables = _columnar_table_names()

    _announce_step(
        "verify",
        "A",
        "defineOneRef and defineManyRefs optional value 1 names an existing columnar table",
    )
    for tref in range(len(dsTable_Name)):
        if dsTable_Type[tref] != _DS_TABLE_TYPE_COLUMNAR:
            continue
        owning_table = dsTable_Name[tref]
        for vref in dsTable_dsVariable_Refs[tref]:
            vtype = dsVariable_Type[vref]
            if vtype not in _REF_VARIABLE_TYPES:
                continue
            var_name = dsVariable_Name[vref]
            line_no = dsVariable_LineNumber[vref]
            dest_table = dsVariable_OptionalValue1[vref]
            if dest_table not in columnar_tables:
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        line_no,
                        f"(Phase 2 verify A) {vtype} {var_name!r} references unknown table "
                        f"{dest_table!r}",
                    )
                )

    _announce_step(
        "verify",
        "B",
        "defineOneRef and defineManyRefs do not reference their owning table",
    )
    for tref in range(len(dsTable_Name)):
        if dsTable_Type[tref] != _DS_TABLE_TYPE_COLUMNAR:
            continue
        owning_table = dsTable_Name[tref]
        for vref in dsTable_dsVariable_Refs[tref]:
            vtype = dsVariable_Type[vref]
            if vtype not in _REF_VARIABLE_TYPES:
                continue
            var_name = dsVariable_Name[vref]
            line_no = dsVariable_LineNumber[vref]
            dest_table = dsVariable_OptionalValue1[vref]
            if dest_table == owning_table:
                raise ValueError(
                    _parse_error(
                        dd_filepath,
                        line_no,
                        f"(Phase 2 verify B) {vtype} {var_name!r} cannot reference its own "
                        f"table {owning_table!r}",
                    )
                )

    _announce_step(
        "verify",
        "C",
        "defineIndexOneRef and defineIndexManyRefs optional value 1 names an AddARow column in the same table",
    )
    for tref in range(len(dsTable_Name)):
        if dsTable_Type[tref] != _DS_TABLE_TYPE_COLUMNAR:
            continue
        owning_table = dsTable_Name[tref]
        column_names = {col_var for col_var, _ in _addarow_columns_for_table(tref)}
        for vref in _variables_of_type(tref, _INDEX_ONE_REF_TYPE):
            index_var = dsVariable_Name[vref]
            key_col = dsVariable_OptionalValue1[vref]
            if key_col in column_names:
                continue
            raise ValueError(
                _parse_error(
                    dd_filepath,
                    dsVariable_LineNumber[vref],
                    f"(Phase 2 verify C) defineIndexOneRef {index_var!r} cites column "
                    f"{key_col!r}, which is not a column in table {owning_table!r}",
                )
            )
        for vref in _variables_of_type(tref, _INDEX_MANY_REFS_TYPE):
            index_var = dsVariable_Name[vref]
            key_col = dsVariable_OptionalValue1[vref]
            if key_col in column_names:
                continue
            raise ValueError(
                _parse_error(
                    dd_filepath,
                    dsVariable_LineNumber[vref],
                    f"(Phase 2 verify C) defineIndexManyRefs {index_var!r} cites column "
                    f"{key_col!r}, which is not a column in table {owning_table!r}",
                )
            )

    if _is_gdscodegen_processor_schema():
        _announce_step(
            "verify",
            "D",
            "skipped (processor schema: dsTable <-> dsVariable cycle allowed for codegen mirror)",
        )
    else:
        _announce_step(
            "verify",
            "D",
            "reference graph has no directed cycle among defineOneRef / defineManyRefs",
        )
        ref_edges = _schema_ref_edges()
        schema_graph = _schema_ref_graph_from_edges(ref_edges)
        cycle_tables = find_reference_cycle(schema_graph)
        if cycle_tables is not None:
            raise ValueError(
                _parse_error(
                    dd_filepath,
                    None,
                    _format_reference_cycle_message(cycle_tables, ref_edges),
                )
            )


def _output_py_path(cli):
    return os.path.splitext(cli.dd_path)[0] + ".py"


def _table_ref_for_name(tbl_name):
    """Row ref in ``dsTable`` for ``tbl_name``, or ``None`` if not in the loaded schema."""
    if tbl_name in dsTable_Name_2Ref:
        return dsTable_Name_2Ref[tbl_name]
    return None


def _variable_refs_for_table(table_ref):
    """Variable row refs for a table, in schema definition order (``dsTable_dsVariable_Refs``)."""
    return dsTable_dsVariable_Refs[table_ref]


def _variables_of_type(table_ref, variable_type):
    """Refs from ``dsTable_dsVariable_Refs`` whose ``dsVariable_Type`` equals ``variable_type``."""
    return [
        vref
        for vref in _variable_refs_for_table(table_ref)
        if dsVariable_Type[vref] == variable_type
    ]


def _first_variable_of_type(table_ref, variable_type):
    """First variable ref of ``variable_type`` in schema order, or ``None``."""
    for vref in _variable_refs_for_table(table_ref):
        if dsVariable_Type[vref] == variable_type:
            return vref
    return None






def _addarow_parameter_default_token(vref):
    """Schema optional token used as ``_<column>=…`` default in ``<table>_AddARow``."""
    vtype = dsVariable_Type[vref]
    n = dsVariable_OptionalValueCount[vref]
    if n <= 0:
        return None
    if vtype in _ONE_REF_VARIABLE_TYPES:
        return dsVariable_OptionalValue2[vref] if n >= 2 else None
    if vtype == "defineManyRefs":
        return None
    if vtype == "defineName":
        col_ref = dsVariable_OptionalValue1[vref]
        line_name = dsVariable_Name[vref]
        if col_ref and col_ref not in ("None", "") and col_ref != line_name:
            return None
        return col_ref
    return dsVariable_OptionalValue1[vref]






def _unquote_schema_string_token(token):
    """If ``token`` is a schema quoted string (e.g. ``\"\"`` → empty), return the inner value."""
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    return None


def _format_python_literal(token):
    if token is None:
        return "None"
    if token == "None":
        return "None"
    unquoted = _unquote_schema_string_token(token)
    if unquoted is not None:
        return repr(unquoted)
    try:
        int(token, 10)
        return token
    except ValueError:
        pass
    try:
        float(token)
        return token
    except ValueError:
        pass
    return repr(token)


def _parameter_default_suffix(vref):
    default = _addarow_parameter_default_token(vref)
    if default is None:
        return ""
    return f"={_format_python_literal(default)}"


def _addarow_column_sort_key(pair):
    """Sort key for signature params: required (no default), then optional; schema order within each."""
    _col_var, vref = pair
    has_default = _addarow_parameter_default_token(vref) is not None
    return (1 if has_default else 0, dsVariable_LineIndex[vref])


def _name_column_storage_variable(vref):
    """Column list that holds row names (``defineName`` line name, or a separate column token)."""
    line_name = dsVariable_Name[vref]
    if dsVariable_OptionalValueCount[vref] >= 1:
        col_ref = dsVariable_OptionalValue1[vref]
        # Third token is the Name column only when it names a column (not a default like None).
        if col_ref and col_ref not in ("None", "") and col_ref != line_name:
            return col_ref
    return line_name






def _addarow_columns_for_table(tref):
    """``(column_var, vref)`` pairs for ``<table>_AddARow`` parameters, in schema order."""
    columns = []
    seen = set()
    for vref in _variable_refs_for_table(tref):
        vtype = dsVariable_Type[vref]
        if vtype not in _ADDAROW_PARAMETER_TYPES:
            continue
        if vtype == "defineName":
            col_var = _name_column_storage_variable(vref)
        else:
            col_var = dsVariable_Name[vref]
        if col_var in seen:
            continue
        seen.add(col_var)
        columns.append((col_var, vref))
    return columns


def _name_storage_column_for_table(tref):
    """Storage list for ``defineName`` in this table, or ``None``."""
    vref = _first_variable_of_type(tref, "defineName")
    if vref is None:
        return None
    return _name_column_storage_variable(vref)


def _all_indexes_for_table(tref):
    """``(index_dict_var, key_column_var, kind)`` per index; *kind* is ``one`` or ``many``."""
    result = []
    for vref in _variables_of_type(tref, _INDEX_ONE_REF_TYPE):
        result.append(
            (
                dsVariable_Name[vref],
                dsVariable_OptionalValue1[vref],
                "one",
            )
        )
    for vref in _variables_of_type(tref, _INDEX_MANY_REFS_TYPE):
        result.append(
            (
                dsVariable_Name[vref],
                dsVariable_OptionalValue1[vref],
                "many",
            )
        )
    return result




def _row_status_column_for_table(tref):
    vref = _first_variable_of_type(tref, "defineRowStatus")
    if vref is None:
        return None
    return dsVariable_Name[vref]










def _referenced_table_name_for_ref(vref):
    """Referenced table from optional value 1 (Phase 2 verify A guarantees it for ref types)."""
    if dsVariable_OptionalValueCount[vref] >= 1 and dsVariable_OptionalValue1[vref]:
        return dsVariable_OptionalValue1[vref]
    vtype = dsVariable_Type[vref]
    parts = dsVariable_Name[vref].split("_", 2)
    if len(parts) >= 2:
        return parts[1]
    raise RuntimeError(f"{vtype} {dsVariable_Name[vref]!r} has no referenced table name")


def _name_storage_column_for_table_name(tbl_name):
    tref = _table_ref_for_name(tbl_name)
    if tref is not None:
        name_col = _name_storage_column_for_table(tref)
        if name_col is not None:
            return name_col
    return f"{tbl_name}_Name"
























def _ref_routine_specs():
    """``(owning_table, dest_table, ref_var, vref, kind)`` per outward ref column; kind is ``one`` or ``many``."""
    specs = []
    for tref in range(len(dsTable_Name)):
        if dsTable_Type[tref] != _DS_TABLE_TYPE_COLUMNAR:
            continue
        owning_table = dsTable_Name[tref]
        for vref in _variable_refs_for_table(tref):
            vtype = dsVariable_Type[vref]
            if vtype == "defineOneRef":
                kind = "one"
            elif vtype == "defineManyRefs":
                kind = "many"
            else:
                continue
            ref_var = dsVariable_Name[vref]
            dest_table = _referenced_table_name_for_ref(vref)
            specs.append((owning_table, dest_table, ref_var, vref, kind))
    return specs


def _applyral_routine_name(owning_table, dest_table, kind):
    suffix = "_Refs" if kind == "many" else "_Ref"
    return f"{owning_table}_ApplyRALTo_{dest_table}{suffix}"
































def _schema_file_path(cli):
    return cli.dd_path

