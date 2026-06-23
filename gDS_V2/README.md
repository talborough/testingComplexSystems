# gDS V2 — Compiler and Exerciser

This project has two tools:

- **gDSCompile** — reads a text file that describes your tables (`.dd`) and writes Python code (`.py`) that stores and manages them.
- **gDSExer** — a practice program. You pick commands from a menu to try that Python code, record what you typed, and play it back later to check nothing broke.

Your application program imports the `.py` file and calls its functions. gDSExer uses the same functions — it is just a safe place to learn them.

---

## The idea

Imagine a spreadsheet, but stored in Python:

- Each **column** is its own **list** (Name list, Kind list, FarmRef list, …).
- Every list in a table has the **same length**. That length is the row count.
- **Row 0** means the first item in every column. **Row 1** means the second item, and so on.

A **reference** (ref) is a row number in **another** table. Example: animal row 0 might store `0` in its FarmRef column to mean “point at farm row 0.” `None` means “points nowhere.”

An **index** is a **dictionary** for fast lookup — like “find the row whose Name is Bessie.”

You write the plan once in a `.dd` file. The compiler writes boring code for you: add a row, delete rows, fix broken pointers, save to JSON.

There is no SQL. No database layer. Just lists, row numbers, and plain Python functions. It's up to you to see if gDS has merit for your application.

---

## A small example

Table **gAnimal**:

```text
         Name       Kind      FarmRef   RowStatus
    0   'Bessie'    'cow'        0         None
    1   'Wilbur'    'pig'        1         None
    2   'Cluck'     'chicken'    None      None
```

- **Name** — every row needs a name (used when printing).
- **Kind** — normal data column.
- **FarmRef** — which farm row this animal points at.
- **RowStatus** — a "flag" on every row (your program decides what it means). Required on every table. It also must be the last column for the table in the `.dd` file. If this column exists for a given row, the entire row has been completely added to the table.

---

## What you write vs what you get

### The `.dd` file (you write this)

A table is a block:

```text
defineTable  gAnimal
  … column lines …
endTable
```

| Keyword | What it means |
|---------|----------------|
| `defineColumn` | Normal data (text, number, etc.) |
| `defineName` | The row’s name (exactly one per table) |
| `defineOneRef` | Points to one row in another table |
| `defineManyRefs` | Points to many rows in another table |
| `defineIndexOneRef` / `defineIndexManyRefs` | Fast lookup dictionary |
| `defineRowStatus` | Status flag (exactly one; last line before `endTable`) |

**Naming rules** (the compiler checks these):

- Table name: no underscore — `gAnimal`, not `g_Animal`
- Column name: starts with table name + `_` — `gAnimal_Kind`
- Ref column: `{yourTable}_{otherTable}_Ref` — example: `gAnimal_gFarm_Ref`

More detail: [gDSCompiler-keywords-and-naming.md](gDSCompiler-keywords-and-naming.md).

### The `.py` file (the compiler writes this)

```bash
./gDSCompile mySchema.dd
```

Creates **`mySchema.py`** next to the `.dd`. Do not edit it by hand — compile again to regenerate.

| Helper function | What it does |
|----------|--------------|
| `{Table}_AddARow` | Add one row |
| `{Table}_DeleteRows` | Remove rows; returns a **RAL** (see below) |
| `{Table}_DumpRows` | Print the table |
| `{Table}_WriteToFile` / `_ReadFromFile` | Save or load JSON |
| `{Own}_ApplyRALTo_{Dest}_Ref` | Fix pointers in table `{Own}` after rows were deleted in `{Dest}` |

---

## Deleting rows and the RAL

When you delete a row, two things happen:

1. Rows below it **slide up** (row 2 might become row 1).
2. Other tables will then store the **old** row numbers.

A **RAL** (Reference Adjustment List) is a cheat sheet from `DeleteRows`. For each **old** row number it says:

| RAL value | Meaning |
|-----------|---------|
| `None` | That row was deleted |
| A number `n` | That row still exists, but now at row `n` |

Example — delete row 1 (`Wilbur`) from gAnimal:

```text
              Old row   Animal      RAL
                  0    'Bessie'      0
                  1    'Wilbur'   None
                  2    'Cluck'       1
```

After the delete, gAnimal has two rows. Cluck used to be row 2; now she is row 1.

**Step 1:** Call `DeleteRows` on one table. You get the RAL.

**Step 2:** Call `ApplyRALTo_…` on each other table that pointed into the deleted table. That updates or clears the old pointers.

You choose **when** to run step 2. gDS does not auto-fix other tables for you.

**Delete modes:**

| Mode | What it deletes |
|------|-----------------|
| `allRows` | Everything |
| `rowStatusValueToDelete` | Rows with a certain RowStatus value |
| `rowReferencesToDelete` | Specific row numbers you list |

---

## Things gDS does NOT do

- **No automatic “fixup across all tables.”** You run delete, then apply, in the order you want.
- **No built-in locking for multiple programs.** If several programs share the data, you design how they take turns (locks, rules, etc.). gDSExer is a good place to practice.

---

## gDSExer (the practice tool)

Run:

```bash
./gDSExer mySchema.dd
```

| You type | What happens |
|----------|--------------|
| `add` | Add a row |
| `delete` | Delete rows (saves the RAL) |
| `apply` | Fix refs using the RAL |
| `adjust` | Change a pointer by hand |
| `dump` | Print one table |
| `rec` / `play` | Record or replay a script |
| `s/d` | Save a “gold” snapshot (while recording) or compare to one (while playing back) |

**Simple test workflow:**

1. Record small scripts that build test data.
2. Record a main script that plays them and hits `s/d` at checkpoints (saved under `myScript_gold/01/`, `02/`, …).
3. Play the main script back. Each `s/d` checks tables match the saved gold — PASS or FAIL.

gDSExer checks whether the **code works**. It does not tell you if your table design makes sense for real life.

Command list: [gDSExer-keywords-and-naming.md](gDSExer-keywords-and-naming.md).

---

## Quick start

```bash
./gDSCompile mySchema.dd    # make mySchema.py
./gDSExer mySchema.dd       # try it in the terminal
```

| Flag | Meaning |
|------|---------|
| `-v` | Print more messages while compiling |
| `-d` | Show internal schema tables (for debugging) |
| `-O` | Use normal Python lists instead of shared-memory lists |

---

## Files in this folder

| File | What it is |
|------|------------|
| `gDSCompile` | Run the compiler |
| `gDSCompiler.py` | Compiler (reads `.dd`) |
| `gDSSchema.py` | Checks that `.dd` is valid |
| `gDSCompileCG.py` | Writes the `.py` file |
| `gDSExer` | The practice program |
| `gDSExerSchema.py` | Connects gDSExer to your schema |

---

## Five questions to ask yourself

| Question | Short answer |
|----------|--------------|
| Where is my data? | In Python lists and dicts — one per column |
| Where do I define tables? | In the `.dd` file |
| What is a RAL? | A map from old row numbers to new ones after a delete |
| Why two steps (delete + apply)? | So **you** control when and how other tables get fixed |
| What is gDSExer for? | Learning and testing — not designing the logical structure of your app |
