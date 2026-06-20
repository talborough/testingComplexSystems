# gDS Compiler — Keywords and Naming Conventions

Summary of the language accepted by **gDSCompile** (see `gDSCompiler.py`, `gDSSchema.py`, `gDSCompileCG.py`). Schema files use the `.dd` extension; compilation produces a sibling `.py` module with the same stem.

---

## Schema file format

- One directive per line; fields are **whitespace-separated tokens**.
- **`#` starts an end-of-line comment**; text after `#` is ignored.
- Blank lines are ignored.
- **Keywords** are reserved tokens (see below). Any other token is an **identifier** (table or column name).
- **Atoms** are `None` or a decimal integer literal; they may appear as optional values.
- Each directive has the form:

  ```text
  <keyword> <name> [<optional-value> …]
  ```

  Up to **three optional values** may follow the name.

---

## Schema keywords

### Table block

| Keyword | Level | Purpose |
|---------|-------|---------|
| `defineTable` | top | Start a **columnar** table; next token is the table name. |
| `endTable` | inner | End the current `defineTable` block. |

### Inner directives (inside `defineTable` … `endTable`)

| Keyword | Storage | Role |
|---------|---------|------|
| `defineColumn` | shared list | Ordinary scalar column (parallel list per row). |
| `defineName` | shared list | Row **name** column (exactly one per table; see naming). |
| `defineRowStatus` | shared list | Row **status** column (exactly one; must be last inner line). |
| `defineOneRef` | shared list | Single reference to another table’s row. |
| `defineManyRefs` | shared list | List of references to another table’s rows. |
| `defineIndexOneRef` | shared dict | Index: row ref → row ref (one-ref column). |
| `defineIndexManyRefs` | shared dict | Index: row ref → list of row refs (many-refs column). |

### Top-level singular shorthands (not inside a table block)

| Keyword | Generated table kind | Purpose |
|---------|---------------------|---------|
| `defineUnary` | `unary` | Single scalar value; **requires optional value 1** (initial value). |
| `defineList` | `list` | Top-level list container. |
| `defineDict` | `dict` | Top-level dict container. |

These expand to one `dsTable` row and one `dsVariable` row; they do **not** use `defineTable` / `endTable`.

---

## Structural rules (load-time verification)

| Rule | Requirement |
|------|-------------|
| **Legal keywords** | Only the keywords above may appear; inner keywords only inside a table block. |
| **Nesting** | `defineTable` / `endTable` must balance; singular shorthands cannot appear inside a block. |
| **Unique names** | Table and variable names must be unique across the schema. |
| **`defineName`** | Exactly **one** per columnar table. |
| **`defineRowStatus`** | Exactly **one** per columnar table; must be the **last** inner directive before `endTable`. |
| **Optional value 1** | Required for `defineIndexOneRef`, `defineIndexManyRefs`, `defineOneRef`, and `defineManyRefs` (see below). |
| **`defineManyRefs`** | Only optional value 1 is allowed (referenced table); **no** optional value 2. |
| **Reference graph** | `defineOneRef` / `defineManyRefs` must point at existing columnar tables, not the owning table, and (except the codegen mirror schema) must not form a directed cycle. |

---

## Optional values by keyword

| Keyword | Optional value 1 | Optional value 2 | Optional value 3 |
|---------|------------------|------------------|------------------|
| `defineColumn` | AddARow default | — | — |
| `defineName` | Name **storage column** if different from line name; else default for AddARow | AddARow default | — |
| `defineRowStatus` | AddARow default | — | — |
| `defineOneRef` | **Referenced table name** (required) | AddARow default | — |
| `defineManyRefs` | **Referenced table name** (required) | *(not allowed)* | — |
| `defineIndexOneRef` | **Key column** to index (required) | — | — |
| `defineIndexManyRefs` | **Key column** to index (required) | — | — |
| `defineUnary` | **Initial value** (required) | — | — |
| `defineList` / `defineDict` | *(schema-specific)* | — | — |

Optional values on AddARow parameters become default argument values in generated `<table>_AddARow`.

---

## Native naming conventions (Phase 3)

These rules are enforced for **columnar** tables. They keep column names, indexes, and references consistent with generated code.

### Table names

- **No underscore** in the table name itself.  
  Example: `gAnimal`, not `g_Animal`.

### Column names (all inner variables)

- Every column name **starts with `{table}_`**.  
  Example: table `gAnimal` → `gAnimal_Name`, `gAnimal_Species_Ref`.

### Suffix rules by directive

| Directive | Name must end with | Example (table `gFarm`) |
|-----------|-------------------|-------------------------|
| `defineName` | `_Name` | `gFarm_Name` |
| `defineRowStatus` | `_RowStatus` | `gFarm_RowStatus` |
| `defineOneRef` | `_Ref` | `gFarm_gAnimal_Ref` |
| `defineManyRefs` | `_Refs` | `gFarm_gHouse_Refs` |

### Reference column shape (`defineOneRef` / `defineManyRefs`)

- Name splits into **exactly three** `_`-separated segments:  
  `{owning}_{referenced-table}_{Ref|Refs}`
- The **middle segment** must not equal the owning table name.
- **Optional value 1** (referenced table) must match the middle segment.

Examples for owning table `gFarm`:

```text
defineOneRef    gFarm_gAnimal_Ref   gAnimal
defineManyRefs  gFarm_gHouse_Refs   gHouse
```

### Index column shape

| Directive | Name pattern | Optional value 1 |
|-----------|--------------|------------------|
| `defineIndexOneRef` | `{table}_{tail}_2Ref` | Must name the indexed column `{table}_{tail}` |
| `defineIndexManyRefs` | `{table}_{tail}_2Refs` | Must name the indexed column `{table}_{tail}` |

Examples for table `dsVariable`:

```text
defineIndexOneRef   dsVariable_Name_2Ref   dsVariable_Name
defineManyRefs      dsVariable_dsTable_Refs dsTable
defineIndexOneRef   dsTable_Name_2Ref      dsTable_Name
```

### Bare column names

For `defineColumn`, `defineName`, and `defineRowStatus`, the **bare name** (text after the first `_` in the full column name) is stored in IR as `dsVariable_BareName` and used in dumps and prompts.

---

## Generated Python naming

For each **columnar** table `{Table}`, the compiler emits:

| Generated symbol | Meaning |
|------------------|---------|
| `{Table}_AddARow(...)` | Append one row; parameters follow AddARow-eligible columns (`defineColumn`, `defineName`, `defineOneRef`, `defineManyRefs`, `defineRowStatus`). |
| `{Table}_DumpRows(...)` | Print row/column contents. |
| `{Table}_DeleteRows(deleteMethod, selectorValue=None)` | Delete rows; returns a **RAL** (Reference Adjustment List). |
| `{Table}_WriteToFile(filespec)` | Serialize table to JSON. |
| `{Table}_ReadFromFile(filespec)` | Load table from JSON. |

For each outward reference from owning table `{Own}` to destination table `{Dest}`:

| Ref kind | Generated routine |
|----------|-------------------|
| one-ref column | `{Own}_ApplyRALTo_{Dest}_Ref` |
| many-refs column | `{Own}_ApplyRALTo_{Dest}_Refs` |

Shared storage in the generated module:

- **List columns** → `gDSMgr.list()` by default, or `[]` with **`-O`** (ordinary containers).
- **Index dicts** → `gDSMgr.dict()` by default, or `{}` with **`-O`**.

Singular shorthands generate a single variable named like the schema line (e.g. `defineUnary count 0` → variable `count`).

---

## Compiler pipeline (reference)

```text
.dd file → Lexer → Parser → AST → IR (dsTable / dsVariable)
         → semantic verification (Phases 1–3) → code generation → .py
```

**CLI** (`gDSCompile`):

| Flag | Effect |
|------|--------|
| `-v` | Verbose phase/verify/generate messages |
| `-d` | Dump IR after load |
| `-O` | Generated `.py` uses ordinary `[]` / `{}` instead of `multiprocessing.Manager` |

The **processor schema** (`gDSIr.dd`, tables `dsTable` and `dsVariable` only) is special: compiling it automatically enables `-O` so the compiler can bootstrap without Manager storage.

---

## Quick example

```text
defineTable     gAnimal
defineName      gAnimal_Name
defineColumn    gAnimal_Kind          None
defineOneRef    gAnimal_gFarm_Ref     gFarm
defineIndexOneRef gAnimal_Name_2Ref   gAnimal_Name
defineRowStatus gAnimal_RowStatus     None
endTable
```

This declares one columnar table with native names, one outward ref to `gFarm`, a name index, and row status — and generates `gAnimal_AddARow`, `gAnimal_DeleteRows`, `gAnimal_ApplyRALTo_gFarm_Ref`, and related helpers in `gAnimal.py` (or the schema stem’s `.py`).
