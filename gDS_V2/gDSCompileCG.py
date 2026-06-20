#!/usr/bin/python3
#
# gDSCompileCG.py - gDS schema Python code generation (emit .py from dsTable/dsVariable IR).
#
# Used by gDSCompile. IR helpers live in gDSSchema.py; this module performs Phase 4 code emission only.
#

import os
import sys
import textwrap

from gDSIr import *

GeneratedCode = ""

# Names injected from gDSSchema per compile.
_SCHEMA_INJECT = (
    "Cli",
    "_ordinary_containers",
    "_announce_step",
    "_output_py_path",
    "_table_ref_for_name",
    "_variable_refs_for_table",
    "_variables_of_type",
    "_first_variable_of_type",
    "_name_column_storage_variable",
    "_addarow_columns_for_table",
    "_name_storage_column_for_table",
    "_all_indexes_for_table",
    "_row_status_column_for_table",
    "_referenced_table_name_for_ref",
    "_name_storage_column_for_table_name",
    "_addarow_parameter_default_token",
    "_ref_routine_specs",
    "_applyral_routine_name",
    "_is_gdscodegen_processor_schema",
    "_DS_TABLE_TYPE_COLUMNAR",
    "_DS_TABLE_TYPE_UNARY",
    "_DS_TABLE_TYPE_LIST",
    "_DS_TABLE_TYPE_DICT",
    "_ADDAROW_PARAMETER_TYPES",
    "_DICT_EMITTING_VARIABLE_TYPES",
    "_LIST_EMITTING_VARIABLE_TYPES",
)


def _inject_schema(schema_mod):
    """Bind schema-driver globals used by codegen helpers."""
    g = globals()
    saved = {name: g[name] for name in _SCHEMA_INJECT if name in g}
    for name in _SCHEMA_INJECT:
        g[name] = getattr(schema_mod, name)
    g["Cli"] = schema_mod.Cli
    return saved


def _restore_schema(saved):
    g = globals()
    for name in _SCHEMA_INJECT:
        if name in saved:
            g[name] = saved[name]
        elif name in g:
            del g[name]


def _parameter_default_suffix(vref):
    default = _addarow_parameter_default_token(vref)
    if default is None:
        return ""
    return f"={_format_python_literal(default)}"


def _unquote_schema_string_token(token):
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


def _gen_list_expr():
    """Generated initializer for a shared list column."""
    return "[]" if _ordinary_containers() else "gDSMgr.list()"


def _gen_dict_expr():
    """Generated initializer for a shared dict column."""
    return "{}" if _ordinary_containers() else "gDSMgr.dict()"


_PROCESSOR_PY_LRU_SLOTS = 3


def _append_generated_code_block(lines, extra_indent=""):
    """Append generated Python lines; ``extra_indent`` prefixes each line (e.g. nested block)."""
    global GeneratedCode
    if not lines:
        return
    body = "\n".join(lines)
    if extra_indent:
        body = textwrap.indent(body, extra_indent)
    GeneratedCode += body
    if not body.endswith("\n"):
        GeneratedCode += "\n"


def _name_column_storage_variable(vref):
    """Column list that holds row names (``defineName`` line name, or a separate column token)."""
    line_name = dsVariable_Name[vref]
    if dsVariable_OptionalValueCount[vref] >= 1:
        col_ref = dsVariable_OptionalValue1[vref]
        # Third token is the Name column only when it names a column (not a default like None).
        if col_ref and col_ref not in ("None", "") and col_ref != line_name:
            return col_ref
    return line_name


def _variable_declaration_lines(vref, declared_names):
    """Lines declaring one shared column (list or dict).

    ``defineName`` does not get its own list; it declares the **Name column** storage variable.
    Optional values on the schema line are defaults for **AddARow**, not load-time ``.append``.
    """
    vname = dsVariable_Name[vref]
    vtype = dsVariable_Type[vref]
    if vtype == "defineName":
        storage = _name_column_storage_variable(vref)
        if storage in declared_names:
            return []
        declared_names.add(storage)
        return [f"{storage} = {_gen_list_expr()}"]
    if vname in declared_names:
        return []
    if vtype in _DICT_EMITTING_VARIABLE_TYPES:
        declared_names.add(vname)
        return [f"{vname} = {_gen_dict_expr()}"]
    if vtype in _LIST_EMITTING_VARIABLE_TYPES:
        declared_names.add(vname)
        return [f"{vname} = {_gen_list_expr()}"]
    declared_names.add(vname)
    return [f"{vname} = {_gen_list_expr()}"]
def _unary_initial_value_token(tref):
    """Optional value 1 on the singular ``defineUnary`` variable row (required at parse time)."""
    vrefs = _variable_refs_for_table(tref)
    if not vrefs:
        return None
    vref = vrefs[0]
    if dsVariable_OptionalValueCount[vref] >= 1:
        return dsVariable_OptionalValue1[vref]
    return None


def _declaration_lines_for_table(tref, tbl_type, tbl_name):
    """All variable-declaration lines for one ``dsTable`` row."""
    if tbl_type == _DS_TABLE_TYPE_COLUMNAR:
        lines = []
        declared_names = set()
        for vref in _variable_refs_for_table(tref):
            lines.extend(_variable_declaration_lines(vref, declared_names))
        return lines
    if tbl_type == _DS_TABLE_TYPE_UNARY:
        lines = [f"{tbl_name} = {_gen_list_expr()}"]
        init = _unary_initial_value_token(tref)
        if init is not None:
            lines.append(f"{tbl_name}.append({_format_python_literal(init)})")
        return lines
    if tbl_type == _DS_TABLE_TYPE_LIST:
        return [f"{tbl_name} = {_gen_list_expr()}"]
    if tbl_type == _DS_TABLE_TYPE_DICT:
        return [f"{tbl_name} = {_gen_dict_expr()}"]
    return []
def _addarow_index_many_append_lines(index_var, keyed_col):
    """Generated lines: append ``thisRef`` to the index list for the row's key value."""
    if _ordinary_containers():
        return [
            f"    _idx_key = {keyed_col}[thisRef]",
            f"    if _idx_key not in {index_var}:",
            f"        {index_var}[_idx_key] = []",
            f"    {index_var}[_idx_key].append(thisRef)",
        ]
    return [
        f"    _idx_key = {keyed_col}[thisRef]",
        f"    if _idx_key not in {index_var}:",
        f"        {index_var}[_idx_key] = gDSMgr.list()",
        f"    {index_var}[_idx_key].append(thisRef)",
    ]


def _addarow_index_duplicate_check_lines(index_var, keyed_col):
    """Generated lines: raise if ``_<keyed_col>`` is already in ``index_var`` (before row insert)."""
    key_param = f"_{keyed_col}"
    return [
        f"    if {key_param} in {index_var}:",
        f"        raise ValueError('Duplicate index key in {index_var}: ' + repr({key_param}))",
    ]


def _row_status_column_for_table(tref):
    vref = _first_variable_of_type(tref, "defineRowStatus")
    if vref is None:
        return None
    return dsVariable_Name[vref]


def _addarow_column_sort_key(pair):
    """Sort key for signature params: required (no default), then optional; schema order within each."""
    _col_var, vref = pair
    has_default = _addarow_parameter_default_token(vref) is not None
    return (1 if has_default else 0, dsVariable_LineIndex[vref])


def _addarow_columns_append_order(columns):
    """Column pairs for ``.append`` calls: all columns except RowStatus, then RowStatus."""
    non_row_status = []
    row_status = []
    for pair in columns:
        if dsVariable_Type[pair[1]] == "defineRowStatus":
            row_status.append(pair)
        else:
            non_row_status.append(pair)
    return non_row_status + row_status


def _addarow_function_lines(tbl_name, tref):
    """``def <table>_AddARow(...)`` and body for one columnar table."""
    columns = _addarow_columns_for_table(tref)
    if not columns:
        return []

    sig_columns = sorted(columns, key=_addarow_column_sort_key)
    param_parts = [
        f"_{col_var}{_parameter_default_suffix(vref)}" for col_var, vref in sig_columns
    ]
    sig_lines = [f"def {tbl_name}_AddARow("]
    sig_lines.extend(f"    {part}," for part in param_parts)
    sig_lines.append("):")

    row_status_col = _row_status_column_for_table(tref)
    table_indexes = _all_indexes_for_table(tref)
    body_lines = []
    for index_var, keyed_col, kind in table_indexes:
        if kind == "one":
            body_lines.extend(_addarow_index_duplicate_check_lines(index_var, keyed_col))
    for col_var, _vref in _addarow_columns_append_order(columns):
        if row_status_col and col_var == row_status_col:
            continue
        body_lines.append(f"    {col_var}.append(_{col_var})")
    if row_status_col:
        body_lines.append(f"    thisRef = len({row_status_col})")
        for index_var, keyed_col, kind in table_indexes:
            if kind == "one":
                body_lines.append(f"    {index_var}[{keyed_col}[thisRef]] = thisRef")
            else:
                body_lines.extend(_addarow_index_many_append_lines(index_var, keyed_col))
        body_lines.append(f"    {row_status_col}.append(_{row_status_col})")
    else:
        row_len_col = columns[-1][0]
        body_lines.append(f"    thisRef = len({row_len_col}) - 1")
        for index_var, keyed_col, kind in table_indexes:
            if kind == "one":
                body_lines.append(f"    {index_var}[{keyed_col}[thisRef]] = thisRef")
            else:
                body_lines.extend(_addarow_index_many_append_lines(index_var, keyed_col))
    body_lines.append("    return thisRef")

    return sig_lines + body_lines + [""]
def _storage_column_for_variable(vref):
    if dsVariable_Type[vref] == "defineName":
        return _name_column_storage_variable(vref)
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


def _dumprows_print_one_ref_lines(element_name, dest_table_name):
    name_col = _name_storage_column_for_table_name(dest_table_name)
    deref_var = f"_deref_{element_name}"
    name_var = f"_deref_name_{element_name}"
    return [
        f"            {deref_var} = {element_name}[rowRef]",
        f"            if {deref_var} is None:",
        f"                {name_var} = 'None(???)'",
        "            else:",
        f"                try:",
        f"                    {name_var} = {name_col}[{deref_var}]",
        "                except IndexError:",
        f"                    {name_var} = '???'",
        "                else:",
        f"                    if {name_var} is None:",
        f"                        {name_var} = '???'",
        f"            print('    %30s = %10s  (%30s)' % ('{element_name}', {deref_var}, {name_var}), file=outFile)",
    ]


def _dumprows_print_many_refs_lines(element_name, dest_table_name):
    name_col = _name_storage_column_for_table_name(dest_table_name)
    refs_var = f"_refs_{element_name}"
    names_var = f"_deref_names_{element_name}"
    entry_var = f"_deref_name_{element_name}"
    return [
        f"            {refs_var} = {element_name}[rowRef]",
        f"            if not {refs_var}:",
        f"                print('    %30s = %10s  (%30s)' % ('{element_name}', {refs_var}, ''), file=outFile)",
        "            else:",
        f"                {names_var} = []",
        f"                for {entry_var} in {refs_var}:",
        f"                    if {entry_var} is None:",
        f"                        {names_var}.append('None(???)')",
        "                    else:",
        f"                        try:",
        f"                            _n = {name_col}[{entry_var}]",
        "                        except IndexError:",
        f"                            {names_var}.append('???')",
        "                        else:",
        f"                            {names_var}.append('???' if _n is None else _n)",
        f"                print('    %30s = %10s  (%30s)' % ('{element_name}', {refs_var}, ', '.join(str(n) for n in {names_var})), file=outFile)",
    ]


def _dumprows_print_column_lines(element_name):
    return [
        f"            print('    %30s = %10s' % ('{element_name}', {element_name}[rowRef]), file=outFile)",
    ]


def _dumprows_index_one_check_lines(index_var, keyed_col):
    return [
        f"            if {index_var}[{keyed_col}[rowRef]] != rowRef:",
        f"                raise ValueError('Bad index value in {index_var}; value = ' + str({keyed_col}[rowRef]))",
        "            else:",
        f'                print(f"                    Good index value in {index_var}[{{{keyed_col}[rowRef]!r}}]: {{rowRef}}", file=outFile)',
    ]


def _dumprows_index_many_check_lines(index_var, keyed_col):
    return [
        f"            _idx_key = {keyed_col}[rowRef]",
        f"            if rowRef not in {index_var}.get(_idx_key, []):",
        f"                raise ValueError('Bad index value in {index_var}; key = ' + repr(_idx_key))",
        "            else:",
        f'                print(f"                    Good index value in {index_var}[{{_idx_key!r}}]: includes {{rowRef}}", file=outFile)',
    ]


def _dumprows_function_lines(tbl_name, tref):
    """``def <table>_DumpRows(...)`` — V1-style table banner and per-row column dump."""
    row_status = _row_status_column_for_table(tref)
    if not row_status:
        return []

    lines = [
        "#",
        f"# Print values out for table '{tbl_name}'",
        "#",
        f"def {tbl_name}_DumpRows(rangeListToDump = None, outFile = sys.stdout):",
        "",
        "    print(f'**************', file=outFile)",
        "    print(f'**************', file=outFile)",
        f"    print('    Table %s has %d entries' % ('{tbl_name}', len({row_status})), file=outFile)",
        "    print(f'**************', file=outFile)",
        "    print(f'**************', file=outFile)",
        "    print(f'', file=outFile)",
        "",
        f"    for rowRef in range(0, len({row_status})):",
        "        if (rangeListToDump is None) or (rowRef in rangeListToDump):",
        "            print('    Row reference = %d' % (rowRef), file=outFile)",
    ]

    seen_columns = set()
    for vref in _variable_refs_for_table(tref):
        vtype = dsVariable_Type[vref]
        if vtype not in _ADDAROW_PARAMETER_TYPES:
            continue
        element_name = _storage_column_for_variable(vref)
        if element_name in seen_columns:
            continue
        seen_columns.add(element_name)
        if vtype == "defineOneRef":
            dest_table = _referenced_table_name_for_ref(vref)
            lines.extend(_dumprows_print_one_ref_lines(element_name, dest_table))
        elif vtype == "defineManyRefs":
            dest_table = _referenced_table_name_for_ref(vref)
            lines.extend(_dumprows_print_many_refs_lines(element_name, dest_table))
        else:
            lines.extend(_dumprows_print_column_lines(element_name))

    for index_var, keyed_col, kind in _all_indexes_for_table(tref):
        if kind == "one":
            lines.extend(_dumprows_index_one_check_lines(index_var, keyed_col))
        else:
            lines.extend(_dumprows_index_many_check_lines(index_var, keyed_col))
    lines.extend(
        [
            "            print('', file=outFile)",
            "",
            "    return",
            "",
        ]
    )
    return lines


def _list_storage_columns_for_table(tref):
    """Parallel list column names deleted/compacted by ``<table>_DeleteRows`` (not index dicts)."""
    cols = []
    seen = set()
    for vref in _variable_refs_for_table(tref):
        vtype = dsVariable_Type[vref]
        if vtype in _DICT_EMITTING_VARIABLE_TYPES:
            continue
        if vtype not in _ADDAROW_PARAMETER_TYPES:
            continue
        col_var = _storage_column_for_variable(vref)
        if col_var in seen:
            continue
        seen.add(col_var)
        cols.append(col_var)
    return cols


def _delete_row_del_lines(tref, indent):
    """``del <column>[rowRef]`` lines for one table (reverse delete pass)."""
    prefix = " " * indent
    return [f"{prefix}del {col_var}[rowRef]" for col_var in _list_storage_columns_for_table(tref)]


def _rebuild_index_lines(tref, tbl_name, row_status_col, indent):
    """Clear and rebuild index dicts from column data after row compaction."""
    indexes = _all_indexes_for_table(tref)
    if not indexes:
        return []
    prefix = " " * indent
    lines = []
    for index_var, _keyed_col, _kind in indexes:
        lines.append(f"{prefix}{index_var}.clear()")
    lines.append(f"{prefix}for rowRef in range(len({row_status_col})):")
    for index_var, keyed_col, kind in indexes:
        if kind == "one":
            lines.append(f"{prefix}    {index_var}[{keyed_col}[rowRef]] = rowRef")
        elif _ordinary_containers():
            lines.extend(
                [
                    f"{prefix}    _idx_key = {keyed_col}[rowRef]",
                    f"{prefix}    {index_var}.setdefault(_idx_key, []).append(rowRef)",
                ]
            )
        else:
            lines.extend(
                [
                    f"{prefix}    _idx_key = {keyed_col}[rowRef]",
                    f"{prefix}    if _idx_key not in {index_var}:",
                    f"{prefix}        {index_var}[_idx_key] = gDSMgr.list()",
                    f"{prefix}    {index_var}[_idx_key].append(rowRef)",
                ]
            )
    lines.append("")
    return lines


def _deleterows_function_lines(tbl_name, tref):
    """``def <table>_DeleteRows(…)`` — forward RAL, reverse delete; returns RAL (no ApplyRAL)."""
    row_status = _row_status_column_for_table(tref)
    if not row_status:
        return []

    del_lines = _delete_row_del_lines(tref, 12)
    rebuild = _rebuild_index_lines(tref, tbl_name, row_status, 4)

    lines = [
        "#",
        f"# Delete rows in table '{tbl_name}'.",
        f"# deleteMethod: \"allRows\" | \"rowStatusValueToDelete\" | \"rowReferencesToDelete\".",
        f"# selectorValue: None (ignored for allRows), a RowStatus value, or a list of row refs.",
        f"# Does not call ApplyRAL; use <owning>_ApplyRALTo_{tbl_name}_Ref or _Refs afterward.",
        f"# Forward pass fills _ral: old row index -> new 'compacted' index, or None if deleted.",
        f"# Reverse pass removes rows where _ral[old] is None. Returns the RAL.",
        "#",
        f"def {tbl_name}_DeleteRows(deleteMethod, selectorValue = None):",
        '    if deleteMethod not in ("allRows", "rowStatusValueToDelete", "rowReferencesToDelete"):',
        "        raise ValueError(",
        f'            "{tbl_name}_DeleteRows: deleteMethod must be \'allRows\', \'rowStatusValueToDelete\', or \'rowReferencesToDelete\', got "',
        "            + repr(deleteMethod)",
        "        )",
        '    if deleteMethod == "rowReferencesToDelete" and selectorValue is None:',
        "        raise ValueError(",
        f'            "{tbl_name}_DeleteRows: rowReferencesToDelete requires selectorValue (list of row refs)"',
        "        )",
        f"    _n = len({row_status})",
        "    _ral = []",
        "    _next_new = 0",
        '    if deleteMethod == "rowReferencesToDelete":',
        "        _dset = set(selectorValue)",
        "    for rowRef in range(_n):",
        '        if deleteMethod == "allRows":',
        "            _delete = True",
        '        elif deleteMethod == "rowStatusValueToDelete":',
        f"            _delete = ({row_status}[rowRef] == selectorValue)",
        "        else:",
        "            _delete = (rowRef in _dset)",
        "        if _delete:",
        "            _ral.append(None)",
        "        else:",
        "            _ral.append(_next_new)",
        "            _next_new += 1",
        "",
        "    for rowRef in range(_n - 1, -1, -1):",
        "        if _ral[rowRef] is None:",
    ]
    if del_lines:
        lines.extend(del_lines)
    else:
        lines.append("            pass")
    lines.extend(
        [
            "        else:",
            "            pass",
            "",
        ]
    )
    lines.extend(rebuild)
    lines.extend(["    return _ral", "", ""])
    return lines
def _many_refs_columns_for_table(tref):
    """Column list variables that hold many-ref rows (each row entry is itself a list)."""
    return {
        dsVariable_Name[vref]
        for vref in _variable_refs_for_table(tref)
        if dsVariable_Type[vref] == "defineManyRefs"
    }


def _json_write_read_function_lines(tbl_name, tref):
    """``WriteToFile`` / ``ReadFromFile`` — persist one table as JSON (columns + indexes)."""
    list_cols = _list_storage_columns_for_table(tref)
    if not list_cols:
        return []
    many_ref_cols = _many_refs_columns_for_table(tref)
    table_indexes = _all_indexes_for_table(tref)

    col_write_entries = []
    for col_var in list_cols:
        if col_var in many_ref_cols:
            col_write_entries.append(f'            "{col_var}": [list(_row) for _row in {col_var}],')
        else:
            col_write_entries.append(f'            "{col_var}": list({col_var}),')

    index_write_entries = []
    for index_var, _keyed_col, kind in table_indexes:
        if kind == "many":
            index_write_entries.append(
                f'            "{index_var}": {{_ik: list(_iv) for _ik, _iv in {index_var}.items()}},'
            )
        else:
            index_write_entries.append(f'            "{index_var}": dict({index_var}),')

    col_read_lines = []
    for col_var in list_cols:
        col_read_lines.append(f"    del {col_var}[:]")
        if col_var in many_ref_cols:
            if _ordinary_containers():
                col_read_lines.extend(
                    [
                        f"    for _row in _cols.get({col_var!r}, []):",
                        f"        {col_var}.append(list(_row))",
                    ]
                )
            else:
                col_read_lines.extend(
                    [
                        f"    for _row in _cols.get({col_var!r}, []):",
                        "        _inner = gDSMgr.list()",
                        "        _inner.extend(_row)",
                        f"        {col_var}.append(_inner)",
                    ]
                )
        else:
            col_read_lines.append(f"    {col_var}.extend(_cols.get({col_var!r}, []))")

    row_status = _row_status_column_for_table(tref)
    index_read_lines = []
    if table_indexes and row_status:
        index_read_lines.extend(
            [
                "    # Rebuild indexes from columns; JSON object keys are strings and may not",
                "    # match in-memory key types (e.g. float timestamps in defineIndexOneRef).",
            ]
        )
        index_read_lines.extend(_rebuild_index_lines(tref, tbl_name, row_status, 4))

    write_lines = [
        "#",
        f"# Write table '{tbl_name}' to JSON file *filespec* (columns and index dicts).",
        "#",
        f"def {tbl_name}_WriteToFile(filespec):",
        "    with open(filespec, \"w\", encoding=\"utf-8\") as _f:",
        "        json.dump(",
        "            {",
        '                "table": ' + repr(tbl_name) + ",",
        '                "columns": {',
    ]
    write_lines.extend(col_write_entries)
    write_lines.append("                },")
    if index_write_entries:
        write_lines.append('                "indexes": {')
        write_lines.extend(index_write_entries)
        write_lines.append("                },")
    else:
        write_lines.append('                "indexes": {},')
    write_lines.extend(
        [
            "            },",
            "            _f,",
            "            indent=2,",
            "        )",
            "",
        ]
    )

    read_lines = [
        "#",
        f"# Read table '{tbl_name}' from JSON file *filespec* (replaces current column/index data).",
        "#",
        f"def {tbl_name}_ReadFromFile(filespec):",
        "    with open(filespec, \"r\", encoding=\"utf-8\") as _f:",
        "        _data = json.load(_f)",
        "    _cols = _data.get(\"columns\", {})",
    ]
    read_lines.extend(col_read_lines)
    read_lines.extend(index_read_lines)
    read_lines.append("")
    return write_lines + read_lines
def _applyral_body_lines_one(owning_table, dest_table, ref_var, vref, kind, row_status):
    """Apply-RAL loop and optional owning-table row deletion (defineOneRef)."""
    tref = _table_ref_for_name(owning_table)
    fn_name = _applyral_routine_name(owning_table, dest_table, kind)
    lines = [
        "    if RAL is None:",
        "        raise ValueError(",
        f'            "{fn_name}: requires RAL"',
        "        )",
        '    if deleteAction not in ("setRefToNone", "deleteRow"):',
        "        raise ValueError(",
        f'            "{fn_name}: deleteAction must be \'setRefToNone\' or \'deleteRow\', got "',
        "            + repr(deleteAction)",
        "        )",
        "    _drows = []",
        f"    for rowRef in range(len({row_status})):",
        f"        _v = {ref_var}[rowRef]",
        "        if _v is None:",
        "            continue",
        "        _adj = RAL[_v]",
        "        if _adj is not None:",
        f"            {ref_var}[rowRef] = _adj",
        "        else:",
        '            if deleteAction == "setRefToNone":',
        f"                {ref_var}[rowRef] = None",
        "            else:",
        "                _drows.append(rowRef)",
    ]
    lines.extend(
        [
            "    if _drows:",
            "        _dset = set(_drows)",
            f"        _n0 = len({row_status})",
            "        _ralB = []",
            "        _nn = 0",
            "        for rowRef in range(_n0):",
            "            if rowRef in _dset:",
            "                _ralB.append(None)",
            "            else:",
            "                _ralB.append(_nn)",
            "                _nn += 1",
            "        for rowRef in sorted(_drows, reverse=True):",
        ]
    )
    lines.extend(_delete_row_del_lines(tref, 12))
    lines.extend(_rebuild_index_lines(tref, owning_table, row_status, 8))
    return lines


def _applyral_body_lines_many(owning_table, dest_table, ref_var, row_status):
    """Apply-RAL for defineManyRefs: drop list entries for deleted dest rows; remap others."""
    fn_name = _applyral_routine_name(owning_table, dest_table, "many")
    lines = [
        "    if RAL is None:",
        "        raise ValueError(",
        f'            "{fn_name}: requires RAL"',
        "        )",
        f"    for rowRef in range(len({row_status})):",
        f"        _refs = {ref_var}[rowRef]",
        "        if not _refs:",
        "            continue",
        "        for _ri in range(len(_refs) - 1, -1, -1):",
        "            _v = _refs[_ri]",
        "            if _v is None:",
        "                continue",
        "            _adj = RAL[_v]",
        "            if _adj is not None:",
        "                _refs[_ri] = _adj",
        "            else:",
        "                del _refs[_ri]",
    ]
    return lines


def _applyral_body_lines(owning_table, dest_table, ref_var, vref, kind, row_status):
    """Shared apply-RAL loop and optional owning-table row deletion."""
    if kind == "many":
        return _applyral_body_lines_many(owning_table, dest_table, ref_var, row_status)
    return _applyral_body_lines_one(
        owning_table, dest_table, ref_var, vref, kind, row_status
    )


def _applyral_function_lines(owning_table, dest_table, ref_var, vref, kind):
    """``def <owning>_ApplyRALTo_<dest>_Ref|_Refs`` for refs into ``dest_table``."""
    tref = _table_ref_for_name(owning_table)
    if tref is None:
        return []
    row_status = _row_status_column_for_table(tref)
    if not row_status:
        return []

    fn_name = _applyral_routine_name(owning_table, dest_table, kind)
    if kind == "many":
        lines = [
            "#",
            f"# Apply a RAL to references in {owning_table} column '{ref_var}' to rows in {dest_table}.",
            f"# No deleteAction: each list entry pointing at a deleted destination row is removed;",
            f"# surviving destination rows are reindexed via the RAL.",
            "#",
            f"def {fn_name}(RAL):",
        ]
    else:
        lines = [
            "#",
            f"# Apply a RAL to references in {owning_table} column '{ref_var}' to rows in {dest_table}.",
            "#",
            f"def {fn_name}(RAL, deleteAction):",
        ]
    lines.extend(_applyral_body_lines(owning_table, dest_table, ref_var, vref, kind, row_status))
    lines.extend(["", ""])
    return lines


def generate_code_step_6_all_applyral():
    """Step 6 — ``ApplyRAL`` per outward ref column kind."""
    emitted = set()
    for owning_table, dest_table, ref_var, vref, kind in _ref_routine_specs():
        key = (owning_table, dest_table, kind)
        if key in emitted:
            continue
        emitted.add(key)
        apply_lines = _applyral_function_lines(
            owning_table, dest_table, ref_var, vref, kind
        )
        if not apply_lines:
            continue
        apply_name = _applyral_routine_name(owning_table, dest_table, kind)
        _append_generated_code_block(
            textwrap.dedent(
                f"""
                #
                # {apply_name}
                #
                """
            ).splitlines()
        )
        _append_generated_code_block(apply_lines)


def generate_code_step_1_py_file_start(out_py_filename, schema_stem):
    """Step 1 — banner, imports, and optional ``gDSMgr``."""
    if _ordinary_containers():
        body = f"""
            # To consume this file in a Python program:
            #
            #     from {schema_stem} import *
            #
            # Start of gDS include file ...
            #
            # Generated by {getattr(Cli, "generator_name", "gDSCodeGenV2")} from {schema_stem}.dd (-O: ordinary list/dict storage)

            import json
            import sys
            """
    else:
        body = f"""
            # To consume this file in a Python program:
            #
            #     from {schema_stem} import *
            #
            # Start of gDS include file ...
            #
            # Generated by {getattr(Cli, "generator_name", "gDSCodeGenV2")} from {schema_stem}.dd

            import json
            import sys
            from multiprocessing import *
            gDSMgr = Manager()
            """
    _append_generated_code_block(textwrap.dedent(body).splitlines())


_SINGULAR_TABLE_TYPE_KEYWORDS = {
    "unary": "defineUnary",
    "list": "defineList",
    "dict": "defineDict",
}


def _table_declaration_section_comment(tbl_name, tbl_type):
    """Banner comment before variable declarations for one ``dsTable`` row."""
    keyword = _SINGULAR_TABLE_TYPE_KEYWORDS.get(tbl_type)
    if keyword is not None:
        return f"# Table {tbl_name} ({keyword})"
    return f"# Table {tbl_name}"


def generate_code_step_2_all_variables():
    """Step 2 — shared list/dict declarations for each table and column."""
    for tref in range(len(dsTable_Name)):
        tbl_name = dsTable_Name[tref]
        tbl_type = dsTable_Type[tref]
        decl_lines = _declaration_lines_for_table(tref, tbl_type, tbl_name)
        _append_generated_code_block(
            [
                "#",
                _table_declaration_section_comment(tbl_name, tbl_type),
                "#",
            ]
        )
        _append_generated_code_block(decl_lines)
        _append_generated_code_block([""])


def generate_code_step_3_all_addarow():
    """Step 3 — ``<table>_AddARow`` for each columnar table."""
    for tref in range(len(dsTable_Name)):
        if dsTable_Type[tref] != _DS_TABLE_TYPE_COLUMNAR:
            continue
        tbl_name = dsTable_Name[tref]
        fn_lines = _addarow_function_lines(tbl_name, tref)
        if not fn_lines:
            continue
        _append_generated_code_block(
            textwrap.dedent(
                f"""
                #
                # {tbl_name}_AddARow
                #
                """
            ).splitlines()
        )
        _append_generated_code_block(fn_lines)


def generate_code_step_4_all_dumprows():
    """Step 4 — ``<table>_DumpRows`` for each columnar table."""
    for tref in range(len(dsTable_Name)):
        if dsTable_Type[tref] != _DS_TABLE_TYPE_COLUMNAR:
            continue
        tbl_name = dsTable_Name[tref]
        fn_lines = _dumprows_function_lines(tbl_name, tref)
        if not fn_lines:
            continue
        _append_generated_code_block(fn_lines)


def generate_code_step_5_all_deleterows():
    """Step 5 — ``<table>_DeleteRows`` (RAL) for each columnar table."""
    for tref in range(len(dsTable_Name)):
        if dsTable_Type[tref] != _DS_TABLE_TYPE_COLUMNAR:
            continue
        tbl_name = dsTable_Name[tref]
        fn_lines = _deleterows_function_lines(tbl_name, tref)
        if not fn_lines:
            continue
        _append_generated_code_block(
            textwrap.dedent(
                f"""
                #
                # {tbl_name}_DeleteRows
                #
                """
            ).splitlines()
        )
        _append_generated_code_block(fn_lines)


def generate_code_step_7_all_json_file_io():
    """Step 7 — ``<table>_WriteToFile`` / ``_ReadFromFile`` (JSON) for each columnar table."""
    for tref in range(len(dsTable_Name)):
        if dsTable_Type[tref] != _DS_TABLE_TYPE_COLUMNAR:
            continue
        tbl_name = dsTable_Name[tref]
        fn_lines = _json_write_read_function_lines(tbl_name, tref)
        if not fn_lines:
            continue
        _append_generated_code_block(
            textwrap.dedent(
                f"""
                #
                # {tbl_name}_WriteToFile / {tbl_name}_ReadFromFile
                #
                """
            ).splitlines()
        )
        _append_generated_code_block(fn_lines)


def _rotate_processor_py_into_lru_cache(out_py):
    """Rotate existing processor ``.py`` into ``.py.1`` … ``.py.3`` before overwrite (processor schema only)."""
    if not _is_gdscodegen_processor_schema():
        return
    slot_paths = [f"{out_py}.{i}" for i in range(1, _PROCESSOR_PY_LRU_SLOTS + 1)]
    newest, mid, oldest = slot_paths[0], slot_paths[1], slot_paths[2]
    if not any(os.path.isfile(p) for p in [out_py] + slot_paths):
        _announce_step(
            "generate",
            "LRU",
            f"no existing {out_py!r} or LRU slots to rotate",
        )
        return
    _announce_step(
        "generate",
        "LRU",
        f"rotate existing {out_py!r} into {_PROCESSOR_PY_LRU_SLOTS}-file LRU cache ",
    )
    if os.path.isfile(oldest):
        os.remove(oldest)
        _announce_step("generate", "LRU", f"removed oldest {oldest!r}")
    if os.path.isfile(mid):
        os.rename(mid, oldest)
        _announce_step("generate", "LRU", f"{mid!r} -> {oldest!r}")
    if os.path.isfile(newest):
        os.rename(newest, mid)
        _announce_step("generate", "LRU", f"{newest!r} -> {mid!r}")
    if os.path.isfile(out_py):
        os.rename(out_py, newest)
        _announce_step("generate", "LRU", f"{out_py!r} -> {newest!r}")


def generate_code_from_tables(schema_mod):
    """Run code-generation steps 1-7 and write the output .py file."""
    saved = _inject_schema(schema_mod)
    try:
        return _generate_code_from_tables_impl()
    finally:
        _restore_schema(saved)


def _generate_code_from_tables_impl():
    """Run code-generation steps 1-7 and write the output .py file."""
    global GeneratedCode
    cli = Cli
    if cli is None:
        raise RuntimeError("generate_code_from_tables called before Cli is set")
    schema_stem = os.path.splitext(os.path.basename(cli.dd_path))[0]
    out_py = _output_py_path(cli)
    _announce_step(
        "Phase",
        4,
        f"Generate Python code and write output file {out_py!r}",
    )
    GeneratedCode = ""
    if _ordinary_containers():
        step1_msg = "start of output .py file (banner comment, import sys)"
        step2_msg = (
            "variable declarations (ordinary [] / {} per table and column "
            "so that the app can run anywhere)"
        )
    else:
        step1_msg = "start of output .py file (banner comment, imports, gDSMgr = Manager())"
        step2_msg = "variable declarations (gDSMgr.list() / gDSMgr.dict() per table and column)"
    _announce_step("generate", 1, step1_msg)
    generate_code_step_1_py_file_start(out_py, schema_stem)
    _announce_step("generate", 2, step2_msg)
    generate_code_step_2_all_variables()
    _announce_step("generate", 3, "<table>_AddARow for each columnar table")
    generate_code_step_3_all_addarow()
    _announce_step("generate", 4, "<table>_DumpRows for each columnar table")
    generate_code_step_4_all_dumprows()
    _announce_step(
        "generate",
        5,
        "<table>_DeleteRows (return Reference Adjustment List (RAL)) for each columnar table",
    )
    generate_code_step_5_all_deleterows()
    _announce_step(
        "generate",
        6,
        "<owning>_ApplyRALTo_<referenced>_Ref / _Refs",
    )
    generate_code_step_6_all_applyral()
    _announce_step(
        "generate",
        7,
        "<table>_WriteToFile / _ReadFromFile (JSON) for each columnar table",
    )
    generate_code_step_7_all_json_file_io()

    _rotate_processor_py_into_lru_cache(out_py)

    with open(out_py, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(GeneratedCode)

    print("")
    print(f"Successfully wrote output file {out_py!r}.")
    if _ordinary_containers():
        print(
            "Compiled with -O: output uses ordinary [] and {} "
            "(not multiprocessing Manager)."
        )
    print("Remember to iterate on the 'RowStatus' column of active tables.")
    print("")
