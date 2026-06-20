#!/usr/bin/python3
#
# gDSCompiler.py - compiler front-end for gDS .dd schema files.
#
# Pipeline: Lexer -> Parser -> AST -> IR (dsTable/dsVariable) -> semantic analysis -> code generation.
#
# Code generation uses gDSCompileCG.py; IR/verify uses gDSSchema.py + gDSIr.py.
#

from __future__ import annotations

import inspect
import os

import gDSCompileCG
import gDSSchema
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Iterator, List, Optional, Sequence, Union


# ---------------------------------------------------------------------------
# AST
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OptionalValues:
    count: int
    value1: Optional[str] = None
    value2: Optional[str] = None
    value3: Optional[str] = None


@dataclass(frozen=True)
class ColumnDef:
    keyword: str
    name: str
    optional: OptionalValues
    line: int
    line_index: int


@dataclass(frozen=True)
class TableDef:
    name: str
    columns: tuple[ColumnDef, ...]
    define_line: int
    end_line: int


@dataclass(frozen=True)
class SingularDef:
    keyword: str
    name: str
    optional: OptionalValues
    line: int


SchemaTopLevel = Union[TableDef, SingularDef]


@dataclass(frozen=True)
class SchemaAst:
    source_path: str
    items: tuple[SchemaTopLevel, ...]


# ---------------------------------------------------------------------------
# Tokens / Lexer
# ---------------------------------------------------------------------------

_TOKEN_KEYWORD = "KEYWORD"
_TOKEN_IDENT = "IDENT"
_TOKEN_ATOM = "ATOM"
_TOKEN_NEWLINE = "NEWLINE"
_TOKEN_EOF = "EOF"

_SCHEMA_KEYWORDS = frozenset(
    {
        "defineTable",
        "endTable",
        "defineColumn",
        "defineIndexOneRef",
        "defineIndexManyRefs",
        "defineOneRef",
        "defineManyRefs",
        "defineName",
        "defineRowStatus",
        "defineUnary",
        "defineList",
        "defineDict",
    }
)


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    column: int


class SchemaLexer:
    """Tokenize a gDS .dd schema file."""

    def __init__(self, source_path: str):
        self.source_path = os.path.abspath(source_path)

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        try:
            fh = open(self.source_path, encoding="utf-8", newline="")
        except OSError as exc:
            raise OSError(f"cannot open schema file {self.source_path!r} ({exc})") from exc

        last_line = 0
        with fh:
            for line_no, raw in enumerate(fh, start=1):
                last_line = line_no
                line = raw.strip()
                if not line:
                    continue
                if "#" in line:
                    line = line.split("#", 1)[0].strip()
                if not line:
                    continue
                parts = line.split()
                for col, part in enumerate(parts):
                    if part in _SCHEMA_KEYWORDS:
                        kind = _TOKEN_KEYWORD
                    elif part == "None" or part.isdigit():
                        kind = _TOKEN_ATOM
                    else:
                        kind = _TOKEN_IDENT
                    tokens.append(Token(kind, part, line_no, col))
                tokens.append(Token(_TOKEN_NEWLINE, "", line_no, len(parts)))

        tokens.append(Token(_TOKEN_EOF, "", last_line or 1, 0))
        return tokens


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class SchemaParseError(ValueError):
    """Raised when the schema token stream is not valid gDS syntax."""


class SchemaParser:
    """Recursive-descent parser: token stream -> SchemaAst."""

    _INNER_KEYWORDS = frozenset(
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
    _SINGULAR_KEYWORDS = frozenset({"defineUnary", "defineList", "defineDict"})

    def __init__(self, tokens: Sequence[Token], source_path: str):
        self.tokens = list(tokens)
        self.source_path = source_path
        self.pos = 0

    def parse(self) -> SchemaAst:
        items: List[SchemaTopLevel] = []
        while not self._at_eof():
            items.append(self._parse_top_level())
        return SchemaAst(source_path=self.source_path, items=tuple(items))

    def _at_eof(self) -> bool:
        return self._peek().kind == _TOKEN_EOF

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.kind != _TOKEN_EOF:
            self.pos += 1
        return tok

    def _expect_keyword(self, *allowed: str) -> str:
        tok = self._advance()
        if tok.kind != _TOKEN_KEYWORD or (allowed and tok.value not in allowed):
            expected = ", ".join(allowed) if allowed else "keyword"
            raise SchemaParseError(
                self._error(tok.line, f"expected {expected}, got {tok.value!r}")
            )
        return tok.value

    def _expect_ident(self) -> str:
        tok = self._advance()
        if tok.kind != _TOKEN_IDENT:
            raise SchemaParseError(
                self._error(tok.line, f"expected identifier, got {tok.value!r}")
            )
        return tok.value

    def _optional_values(self, start_line: int) -> OptionalValues:
        values: List[str] = []
        while self._peek().kind in (_TOKEN_IDENT, _TOKEN_ATOM):
            values.append(self._advance().value)
        n = min(len(values), 3)
        return OptionalValues(
            count=n,
            value1=values[0] if n >= 1 else None,
            value2=values[1] if n >= 2 else None,
            value3=values[2] if n >= 3 else None,
        )

    def _consume_newline(self, line: int) -> None:
        if self._peek().kind == _TOKEN_NEWLINE and self._peek().line == line:
            self._advance()

    def _parse_top_level(self) -> SchemaTopLevel:
        kw = self._expect_keyword()
        if kw == "defineTable":
            return self._parse_table()
        if kw in self._SINGULAR_KEYWORDS:
            return self._parse_singular(kw)
        raise SchemaParseError(
            self._error(self._peek().line, f"unexpected top-level keyword {kw!r}")
        )

    def _parse_singular(self, keyword: str) -> SingularDef:
        line = self.tokens[self.pos - 1].line
        name = self._expect_ident()
        optional = self._optional_values(line)
        self._consume_newline(line)
        return SingularDef(keyword=keyword, name=name, optional=optional, line=line)

    def _parse_table(self) -> TableDef:
        define_line = self.tokens[self.pos - 1].line
        name = self._expect_ident()
        self._consume_newline(define_line)
        columns: List[ColumnDef] = []
        line_index = 0
        while True:
            tok = self._peek()
            if tok.kind == _TOKEN_KEYWORD and tok.value == "endTable":
                end_line = tok.line
                self._advance()
                self._consume_newline(end_line)
                return TableDef(
                    name=name,
                    columns=tuple(columns),
                    define_line=define_line,
                    end_line=end_line,
                )
            if tok.kind == _TOKEN_KEYWORD and tok.value in self._INNER_KEYWORDS:
                col_kw = self._advance().value
                col_line = tok.line
                col_name = self._expect_ident()
                optional = self._optional_values(col_line)
                columns.append(
                    ColumnDef(
                        keyword=col_kw,
                        name=col_name,
                        optional=optional,
                        line=col_line,
                        line_index=line_index,
                    )
                )
                line_index += 1
                self._consume_newline(col_line)
                continue
            raise SchemaParseError(
                self._error(tok.line, f"expected inner directive or endTable, got {tok.value!r}")
            )

    def _error(self, line: int, message: str) -> str:
        driver_line = inspect.currentframe().f_back.f_lineno
        return f"gDSCompile:{driver_line}: {self.source_path}:{line}: {message}"


# ---------------------------------------------------------------------------
# IR builder + compiler driver
# ---------------------------------------------------------------------------


def _clear_ir_tables():
    for name in (
        "dsTable_Name",
        "dsTable_dsVariable_Refs",
        "dsTable_Type",
        "dsTable_DefineLineNumber",
        "dsTable_DefineLineIndex",
        "dsTable_EndLineNumber",
        "dsTable_EndLineIndex",
        "dsTable_RowStatus",
        "dsVariable_Name",
        "dsVariable_BareName",
        "dsVariable_dsTable_Ref",
        "dsVariable_Type",
        "dsVariable_OptionalValueCount",
        "dsVariable_OptionalValue1",
        "dsVariable_OptionalValue2",
        "dsVariable_OptionalValue3",
        "dsVariable_LineNumber",
        "dsVariable_LineIndex",
        "dsVariable_RowStatus",
    ):
        getattr(gDSSchema, name)[:] = []
    gDSSchema.dsTable_Name_2Ref.clear()
    gDSSchema.dsVariable_Name_2Ref.clear()


@dataclass
class CompileOptions:
    dd_path: str
    verbose: bool = False
    dump: bool = False
    ordinary_containers: bool = False
    generator_name: str = "gDSCompile"


class GDSCompiler:
    """Compile a gDS .dd schema to a generated Python module."""

    def compile(self, options: CompileOptions) -> str:
        dd_path = os.path.abspath(options.dd_path)
        if not dd_path.endswith(".dd"):
            raise ValueError("schema path must be a full filespec ending with .dd")

        gDSSchema.Cli = SimpleNamespace(
            dd_path=dd_path,
            verbose=options.verbose,
            dump=options.dump,
            ordinary_containers=options.ordinary_containers,
            generator_name=options.generator_name,
        )
        gDSSchema._verify_codegen_mirror_is_plain()

        gDSSchema._announce_step("Phase", 0, f"lex and parse {dd_path!r}")
        tokens = SchemaLexer(dd_path).tokenize()
        ast = SchemaParser(tokens, dd_path).parse()

        gDSSchema._announce_step("Phase", 1, "lower AST to IR (dsTable / dsVariable)")
        _clear_ir_tables()
        self._build_ir_from_ast(ast)

        gDSSchema.verify_schema_phase_1_f(dd_path)
        gDSSchema.verify_schema_phase_1_g(dd_path)
        gDSSchema.verify_schema_phase_2(dd_path)
        gDSSchema.verify_schema_phase_3_native_naming(dd_path)

        gDSSchema.apply_processor_schema_O_mode(dd_path)
        gDSSchema._dump_loaded_schema_tables()
        gDSCompileCG.generate_code_from_tables(gDSSchema)
        return os.path.splitext(dd_path)[0] + ".py"

    def _build_ir_from_ast(self, ast: SchemaAst) -> None:
        dd_path = ast.source_path
        for item in ast.items:
            if isinstance(item, SingularDef):
                self._build_singular_ir(dd_path, item)
            else:
                self._build_table_ir(dd_path, item)

    def _parse_error(self, schema_path, schema_line_no, message):
        driver_line = inspect.currentframe().f_back.f_lineno
        dd_line = schema_line_no if schema_line_no is not None else "<None>"
        return f"gDSCompile:{driver_line}: {schema_path}:{dd_line}: {message}"

    def _build_singular_ir(self, dd_path: str, node: SingularDef) -> None:
        if node.keyword not in gDSSchema._TOP_LEVEL_SINGULAR_ROW_SPECS:
            raise ValueError(
                self._parse_error(dd_path, node.line, f"unknown singular keyword {node.keyword!r}")
            )
        if node.keyword == "defineUnary" and node.optional.count < 1:
            raise ValueError(
                self._parse_error(
                    dd_path,
                    node.line,
                    f"(Verify B) {node.keyword!r} {node.name!r} requires the initial value "
                    "as the first optional value",
                )
            )
        tbl_t, col_t = gDSSchema._TOP_LEVEL_SINGULAR_ROW_SPECS[node.keyword]
        try:
            singular_variable_refs = gDSSchema._parse_list()
            tref = gDSSchema.dsTable_AddARow(
                _dsTable_Name=node.name,
                _dsTable_dsVariable_Refs=singular_variable_refs,
                _dsTable_Type=tbl_t,
                _dsTable_DefineLineNumber=node.line,
                _dsTable_DefineLineIndex=gDSSchema._NAME_FIELD_COL,
                _dsTable_EndLineNumber=node.line,
                _dsTable_EndLineIndex=gDSSchema._NAME_FIELD_COL,
                _dsTable_RowStatus="parse",
            )
            vref = gDSSchema.dsVariable_AddARow(
                _dsVariable_Name=node.name,
                _dsVariable_Type=col_t,
                _dsVariable_OptionalValueCount=node.optional.count,
                _dsVariable_OptionalValue1=node.optional.value1,
                _dsVariable_OptionalValue2=node.optional.value2,
                _dsVariable_OptionalValue3=node.optional.value3,
                _dsVariable_LineNumber=node.line,
                _dsVariable_LineIndex=0,
                _dsVariable_dsTable_Ref=tref,
                _dsVariable_BareName=gDSSchema._bare_name_for_schema_variable(col_t, node.name),
                _dsVariable_RowStatus="parse",
            )
            singular_variable_refs.append(vref)
        except KeyError as exc:
            raise ValueError(
                self._parse_error(
                    dd_path,
                    node.line,
                    f"(Verify C) duplicate table or variable name ({exc})",
                )
            ) from exc

    def _build_table_ir(self, dd_path: str, node: TableDef) -> None:
        name_directive_seen = False
        row_status_seen = False
        current_table_variable_refs = gDSSchema._parse_list()
        try:
            current_ds_table_row = gDSSchema.dsTable_AddARow(
                _dsTable_Name=node.name,
                _dsTable_dsVariable_Refs=current_table_variable_refs,
                _dsTable_Type=gDSSchema._DS_TABLE_TYPE_COLUMNAR,
                _dsTable_DefineLineNumber=node.define_line,
                _dsTable_DefineLineIndex=gDSSchema._NAME_FIELD_COL,
                _dsTable_EndLineNumber=None,
                _dsTable_EndLineIndex=None,
                _dsTable_RowStatus="parse",
            )
        except KeyError as exc:
            raise ValueError(
                self._parse_error(
                    dd_path,
                    node.define_line,
                    f"(Verify C) duplicate table name ({exc})",
                )
            ) from exc

        for col in node.columns:
            if col.keyword == "defineName" and name_directive_seen:
                raise ValueError(
                    self._parse_error(
                        dd_path,
                        col.line,
                        "(Verify E) exactly one defineName per table (Name column)",
                    )
                )
            if row_status_seen:
                if col.keyword == "defineRowStatus":
                    raise ValueError(
                        self._parse_error(
                            dd_path,
                            col.line,
                            "(Verify D) exactly one defineRowStatus per table (RowStatus must be last)",
                        )
                    )
                raise ValueError(
                    self._parse_error(
                        dd_path,
                        col.line,
                        "(Verify D) defineRowStatus must be the last inner directive "
                        "before endTable (nothing after RowStatus)",
                    )
                )
            try:
                vref = gDSSchema.dsVariable_AddARow(
                    _dsVariable_Name=col.name,
                    _dsVariable_Type=col.keyword,
                    _dsVariable_OptionalValueCount=col.optional.count,
                    _dsVariable_OptionalValue1=col.optional.value1,
                    _dsVariable_OptionalValue2=col.optional.value2,
                    _dsVariable_OptionalValue3=col.optional.value3,
                    _dsVariable_LineNumber=col.line,
                    _dsVariable_LineIndex=col.line_index,
                    _dsVariable_dsTable_Ref=current_ds_table_row,
                    _dsVariable_BareName=gDSSchema._bare_name_for_schema_variable(
                        col.keyword, col.name
                    ),
                    _dsVariable_RowStatus="parse",
                )
                current_table_variable_refs.append(vref)
                if col.keyword == "defineName":
                    name_directive_seen = True
                if col.keyword == "defineRowStatus":
                    row_status_seen = True
            except KeyError as exc:
                raise ValueError(
                    self._parse_error(
                        dd_path,
                        col.line,
                        f"(Verify C) duplicate variable name ({exc})",
                    )
                ) from exc

        if not name_directive_seen:
            raise ValueError(
                self._parse_error(
                    dd_path,
                    node.end_line,
                    "(Verify E) each table must have exactly one defineName (Name column)",
                )
            )
        if not row_status_seen:
            raise ValueError(
                self._parse_error(
                    dd_path,
                    node.end_line,
                    "(Verify D) each table must have exactly one defineRowStatus "
                    "(RowStatus column), last before endTable",
                )
            )
        gDSSchema.dsTable_EndLineNumber[current_ds_table_row] = node.end_line
        gDSSchema.dsTable_EndLineIndex[current_ds_table_row] = gDSSchema._KW_FIELD_COL
