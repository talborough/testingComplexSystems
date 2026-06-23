# gDS Compiler — Schema Language (`.dd` files)

This document lists the words (keywords) you can use in a schema - `.dd` file and the naming rules the compiler enforces.

**gDSCompile** reads `something.dd` and writes `something.py`.

---

## How to write a line

Each line is one instruction:

```text
<keyword> <name> [<extra-value> …]
```

- Words are separated by spaces.
- `#` starts a comment (rest of line is ignored).
- A **keyword** is a special word from the tables below.
- A **name** is your table or column name.
- An **extra value** can be `None`, a number, or another name. Most lines have zero, one, or two extra values.

---

## Table block

A normal table looks like this:

```text
defineTable  gAnimal
defineName        gAnimal_Name
defineColumn      gAnimal_Kind          None
defineOneRef      gAnimal_gFarm_Ref     gFarm
defineRowStatus   gAnimal_RowStatus     None
endTable
```

| Keyword | Meaning |
|---------|---------|
| `defineTable` | Start a table. Next word is the table name. |
| `endTable` | End the table. |

### Column keywords (go inside `defineTable` … `endTable`)

| Keyword | Stored as | Plain English |
|---------|-----------|---------------|
| `defineColumn` | Python list | One value per row (Kind, Age, …) |
| `defineName` | Python list | The name of each row — **required, one per table** |
| `defineRowStatus` | Python list | A status flag per row — **required, one per table, must be last** |
| `defineOneRef` | Python list | One row number pointing into another table |
| `defineManyRefs` | Python list | A list of row numbers pointing into another table |
| `defineIndexOneRef` | Python dict | Quick lookup for a one-ref column |
| `defineIndexManyRefs` | Python dict | Quick lookup for a many-refs column |

### Stand-alone items (NOT inside a table block)

| Keyword | Meaning |
|---------|---------|
| `defineUnary` | One single value (not a table). First extra value = starting value (**required**). |
| `defineList` | One Python list |
| `defineDict` | One Python dictionary |

---

## Rules the compiler checks

| Rule | What it means |
|------|----------------|
| Legal words only | Use only the keywords above |
| Balanced blocks | Every `defineTable` has a matching `endTable` |
| Unique names | No two tables or columns with the same name |
| Name column | Exactly one `defineName` per table |
| RowStatus column | Exactly one `defineRowStatus` per table; it must be the last line before `endTable` |
| References | A ref must point at a real table (not itself). Refs cannot go in a circle. |
| Indexes | Must say which column they index |

---

## Extra values on each line

Most extra values become **default arguments** when you add a row (`AddARow`). Ref and index lines use the first extra value differently:

| Keyword | 1st extra value | 2nd extra value |
|---------|-----------------|-----------------|
| `defineColumn` | Default when adding a row | — |
| `defineName` | Default for name (usually unused) | Another default (rare) |
| `defineRowStatus` | Default when adding a row | — |
| `defineOneRef` | **Which table** this points to (**required**) | Default when adding a row |
| `defineManyRefs` | **Which table** this points to (**required**) | — |
| `defineIndexOneRef` | **Which column** to index (**required**) | — |
| `defineIndexManyRefs` | **Which column** to index (**required**) | — |
| `defineUnary` | **Starting value** (**required**) | — |

---

## Naming rules

The compiler will **reject** bad names. Patterns:

| What | Rule | Good example | Bad example |
|------|------|--------------|-------------|
| Table | No `_` in the name | `gAnimal` | `g_Animal` |
| Any column | Starts with `{table}_` | `gAnimal_Kind` | `Kind` |
| Name column | Ends with `_Name` | `gFarm_Name` | `gFarm_Title` |
| RowStatus | Ends with `_RowStatus` | `gFarm_RowStatus` | `gFarm_Status` |
| One ref | Ends with `_Ref`, three parts | `gFarm_gAnimal_Ref` | `gFarm_Animal` |
| Many refs | Ends with `_Refs`, three parts | `gFarm_gHouse_Refs` | `gFarm_Houses` |
| Index (one) | Ends with `_2Ref` | `gAnimal_Name_2Ref` | `gAnimal_NameIndex` |
| Index (many) | Ends with `_2Refs` | `gFarm_gHouse_2Refs` | `gFarm_Index` |

**Ref name pattern:** `{yourTable}_{otherTable}_Ref` — the middle part must match the table named in the 1st extra value.

```text
defineOneRef    gFarm_gAnimal_Ref   gAnimal
defineManyRefs  gFarm_gHouse_Refs   gHouse
```

**Index pattern:** the 1st extra value names the column being indexed.

```text
defineIndexOneRef  gAnimal_Name_2Ref   gAnimal_Name
```

**Bare name** — the part after the first `_` in a column name (`Kind` from `gAnimal_Kind`). Used in printouts and gDSExer prompts.

---

## What Python code gets generated

For each table `gAnimal`, the compiler writes functions like:

| Function | What it does |
|----------|--------------|
| `gAnimal_AddARow(...)` | Add a row |
| `gAnimal_DeleteRows(...)` | Delete rows; returns a **RAL** |
| `gAnimal_DumpRows(...)` | Print the table |
| `gAnimal_WriteToFile` / `_ReadFromFile` | Save or load JSON |

For each pointer column from `gFarm` into `gAnimal`, it also writes:

| Kind | Function |
|------|----------|
| One pointer | `gFarm_ApplyRALTo_gAnimal_Ref` |
| Many pointers | `gFarm_ApplyRALTo_gAnimal_Refs` |

**RAL** = after a delete, a list that says “old row 2 is now row 1” or “old row 1 is gone.”

By default, columns use **shared-memory** lists (so multiple programs can see the same data). Use flag **`-O`** for normal Python `[]` and `{}`.

---

## Compiler command

```bash
./gDSCompile mySchema.dd
```

| Flag | Meaning |
|------|---------|
| `-v` | More printout while compiling |
| `-d` | Show internal tables (debugging) |
| `-O` | Normal lists, not shared-memory |

---

## Full tiny example

```text
defineTable       gAnimal
defineName        gAnimal_Name
defineColumn      gAnimal_Kind          None
defineOneRef      gAnimal_gFarm_Ref     gFarm
defineIndexOneRef gAnimal_Name_2Ref     gAnimal_Name
defineRowStatus   gAnimal_RowStatus     None
endTable
```

This produces code to create the necesssary tables plus helper routines `gAnimal_AddARow`, `gAnimal_DeleteRows`, `gAnimal_ApplyRALTo_gFarm_Ref`, and the rest in `mySchema.py`.
