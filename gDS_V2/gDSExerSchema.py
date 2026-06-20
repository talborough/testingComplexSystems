#!/usr/bin/python3
#
# gDSExerSchema - load a gDS .dd schema (via gDSSchema / gDSIr) and bind a generated
# .py module for use by gDSExer.
#

import importlib.util
import os
import re
import sys
from types import SimpleNamespace

import gDSSchema

_SCHEMA_REQUIRED = object()
_DS_TABLE_TYPE_COLUMNAR = "columnar"


def _load_schema_module():
    return gDSSchema


def _resolve_dd_basename(dd_path):
    dd_path = os.path.abspath(dd_path)
    if not dd_path.endswith(".dd"):
        raise ValueError(f"schema path must end with .dd: {dd_path!r}")
    if not os.path.isfile(dd_path):
        raise FileNotFoundError(dd_path)
    return dd_path[:-3]


_GDSMGR_CONTAINER_DECL = re.compile(
    r"^\s*\w+\s*=\s*gDSMgr\.(?:list|dict)\(\)\s*$"
)
_ORDINARY_CONTAINER_DECL = re.compile(r"^\s*\w+\s*=\s*(?:\[\]|\{\})\s*$")


def _detect_ordinary_containers_from_py(py_path):
    """True when generated storage uses ordinary [] / {} rather than gDSMgr."""
    with open(py_path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith(("def ", "class ")):
                break
            if "gDSMgr = Manager()" in line or _GDSMGR_CONTAINER_DECL.match(line):
                return False
            if _ORDINARY_CONTAINER_DECL.match(line):
                return True
    return False


def _load_gds_module(py_path):
    py_path = os.path.abspath(py_path)
    if not os.path.isfile(py_path):
        raise FileNotFoundError(py_path)
    mod_name = os.path.splitext(os.path.basename(py_path))[0]
    spec = importlib.util.spec_from_file_location(mod_name, py_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load generated module from {py_path!r}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _ref_display_label(owning_table, ref_col):
    prefix = f"{owning_table}_"
    if ref_col.startswith(prefix):
        return ref_col[len(prefix) :]
    return ref_col


def _addarow_param_heading(table_name, col_var, vtype, bare_name):
    """Label for one AddARow value in create-row summaries (e.g. ``_Name``, ``gHouse_Ref``)."""
    if vtype in ("defineOneRef", "defineManyRefs"):
        return _ref_display_label(table_name, col_var)
    if bare_name:
        return f"_{bare_name}"
    return f"_{col_var}"


def _schema_default_for_vref(cg, vref):
    if cg.dsVariable_Type[vref] == "defineManyRefs":
        return _SCHEMA_REQUIRED
    if cg._parameter_default_suffix(vref):
        return cg._addarow_parameter_default_token(vref)
    return _SCHEMA_REQUIRED


def _addarow_params_for_table(cg, gds, table_name):
    tref = cg._table_ref_for_name(table_name)
    params = []
    columns = cg._addarow_columns_for_table(tref)
    for col_var, vref in columns:
        vtype = cg.dsVariable_Type[vref]
        many = vtype == "defineManyRefs"
        dest_table = cg._referenced_table_name_for_ref(vref) if vtype in (
            "defineOneRef",
            "defineManyRefs",
        ) else None
        dest_name_col = None
        if dest_table is not None:
            dest_tref = cg._table_ref_for_name(dest_table)
            dest_name_col_name = cg._name_storage_column_for_table(dest_tref)
            dest_name_col = getattr(gds, dest_name_col_name)
        bare_name = cg.dsVariable_BareName[vref]
        params.append(
            SimpleNamespace(
                col_var=col_var,
                column_label=cg.dsVariable_Name[vref],
                vref=vref,
                vtype=vtype,
                many=many,
                dest_table=dest_table,
                dest_name_col=dest_name_col,
                heading=_addarow_param_heading(table_name, col_var, vtype, bare_name),
                schema_default=_schema_default_for_vref(cg, vref),
                required=cg._parameter_default_suffix(vref) == "",
            )
        )
    return params


def _build_display_specs(cg, gds, columnar_tables):
    specs = {}
    ref_types = {"defineOneRef", "defineManyRefs"}
    for table in columnar_tables:
        tref = cg._table_ref_for_name(table)
        name_col_name = cg._name_storage_column_for_table(tref)
        name_col = getattr(gds, name_col_name) if name_col_name else None
        row_status_name = cg._row_status_column_for_table(tref)
        row_status_col = getattr(gds, row_status_name)
        ref_specs = []
        extra_fields = []
        for vref in cg._variable_refs_for_table(tref):
            vtype = cg.dsVariable_Type[vref]
            col_name = cg.dsVariable_Name[vref]
            if vtype in ref_types:
                dest = cg._referenced_table_name_for_ref(vref)
                dest_name_col_name = cg._name_storage_column_for_table(
                    cg._table_ref_for_name(dest)
                )
                dest_name_col = getattr(gds, dest_name_col_name)
                label = _ref_display_label(table, col_name)
                if vtype == "defineManyRefs":
                    ref_specs.append((label, getattr(gds, col_name), dest_name_col, True))
                else:
                    ref_specs.append((label, getattr(gds, col_name), dest_name_col))
            elif vtype == "defineColumn":
                bare = cg.dsVariable_BareName[vref]
                extra_fields.append((bare, getattr(gds, col_name)))
        specs[table] = (name_col, ref_specs, row_status_col, tuple(extra_fields))
    return specs


def _build_ref_column_dest_table(cg):
    dest_by_column = {}
    for owning, dest, ref_var, _vref, kind in cg._ref_routine_specs():
        dest_by_column[ref_var] = dest
    return dest_by_column


def _build_ref_routines(cg, gds):
    routines = []
    for owning, dest, ref_var, _vref, kind in cg._ref_routine_specs():
        many = kind == "many"
        apply_name = cg._applyral_routine_name(owning, dest, kind)
        apply_fn = getattr(gds, apply_name)
        routines.append((apply_name, apply_fn, owning, dest, many))
    return routines


def _build_adjust_targets(cg, gds, columnar_tables):
    """Selectable ref columns for the exerciser adjust command (not index dicts)."""
    ref_types = {"defineOneRef", "defineManyRefs"}
    targets = []
    for table in columnar_tables:
        tref = cg._table_ref_for_name(table)
        for vref in cg._variable_refs_for_table(tref):
            vtype = cg.dsVariable_Type[vref]
            if vtype not in ref_types:
                continue
            col_name = cg.dsVariable_Name[vref]
            dest = cg._referenced_table_name_for_ref(vref)
            dest_tref = cg._table_ref_for_name(dest)
            dest_name_col = getattr(
                gds, cg._name_storage_column_for_table(dest_tref)
            )
            owning_name_col = getattr(
                gds, cg._name_storage_column_for_table(tref)
            )
            short = _ref_display_label(table, col_name)
            targets.append(
                SimpleNamespace(
                    label=f"{table} {short}",
                    kind="ref_many" if vtype == "defineManyRefs" else "ref_one",
                    owning_table=table,
                    dest_table=dest,
                    col_var=col_name,
                    storage=getattr(gds, col_name),
                    owning_name_col=owning_name_col,
                    dest_name_col=dest_name_col,
                )
            )
    return targets


def _build_fn_map(gds, columnar_tables, suffix):
    fns = {}
    for table in columnar_tables:
        name = f"{table}_{suffix}"
        fns[table] = getattr(gds, name)
    return fns


def _build_schema_column_defaults(cg, columnar_tables):
    defaults = {}
    for table in columnar_tables:
        tref = cg._table_ref_for_name(table)
        for _col_var, vref in cg._addarow_columns_for_table(tref):
            col = cg.dsVariable_Name[vref]
            defaults[col] = _schema_default_for_vref(cg, vref)
    return defaults


class GDSExerContext:
    """Runtime bindings for one (.dd, .py) schema pair."""

    def __init__(self, dd_path, py_path):
        self.dd_path = os.path.abspath(dd_path)
        self.py_path = os.path.abspath(py_path)
        self.schema_stem = os.path.splitext(os.path.basename(self.dd_path))[0]

        self.codegen = _load_schema_module()
        self._parse_schema()
        self.ordinary_containers = _detect_ordinary_containers_from_py(self.py_path)
        self.gds = _load_gds_module(self.py_path)
        self.gDSMgr = getattr(self.gds, "gDSMgr", None)

        self.columnar_tables = [
            self.codegen.dsTable_Name[tref]
            for tref in range(len(self.codegen.dsTable_Name))
            if self.codegen.dsTable_Type[tref] == _DS_TABLE_TYPE_COLUMNAR
        ]
        if not self.columnar_tables:
            raise ValueError(f"no columnar tables in {self.dd_path!r}")

        # Schema file order (matches menu numbering in PVHTSGExer-style exercisers).
        self.display_table_order = tuple(self.columnar_tables)
        self.delete_fns = _build_fn_map(self.gds, self.columnar_tables, "DeleteRows")
        self.write_fns = _build_fn_map(self.gds, self.columnar_tables, "WriteToFile")
        self.dump_fns = _build_fn_map(self.gds, self.columnar_tables, "DumpRows")
        self.add_fns = _build_fn_map(self.gds, self.columnar_tables, "AddARow")
        self.ref_routines = _build_ref_routines(self.codegen, self.gds)
        self.adjust_targets = _build_adjust_targets(
            self.codegen, self.gds, self.columnar_tables
        )
        self.display_specs = _build_display_specs(
            self.codegen, self.gds, self.columnar_tables
        )
        self.ref_column_dest_table = _build_ref_column_dest_table(self.codegen)
        self.schema_column_defaults = _build_schema_column_defaults(
            self.codegen, self.columnar_tables
        )
        self.addarow_params = {
            table: _addarow_params_for_table(self.codegen, self.gds, table)
            for table in self.columnar_tables
        }

    def _parse_schema(self):
        cg = self.codegen
        _resolve_dd_basename(self.dd_path)
        cg.Cli = SimpleNamespace(
            dd_path=self.dd_path,
            verbose=False,
            dump=False,
            ordinary_containers=False,
        )
        cg.parseSchemaFileToTables()


def load_exer_context(dd_path, py_path):
    """Load *dd_path* into gDS tables and bind callables from *py_path*."""
    return GDSExerContext(dd_path, py_path)
