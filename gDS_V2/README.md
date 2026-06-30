# gDS V2 — Compiler and Exerciser

This directory contains two tools:

- **gDSCompile** — This program reads a text file that describes your tables/schema (`.dd`) and writes Python code (`.py`) that creates the tables and manages them.
- **gDSExer** — This program works with the `.dd` and `.py` files from above. You pick commands from a menu to use the Python tables and helper code; you can also record what you type and play the recording back later to check nothing broke.

Your application program imports the `.py` file and calls its functions. gDSExer uses the same file and functions — it is just a safe, handy place to learn how to use them.

To add to what's below see: [gDSCompiler-keywords-and-naming.md](gDSCompiler-keywords-and-naming.md) and: [gDSExer-keywords-and-naming.md](gDSExer-keywords-and-naming.md).

gDS V2 still uses the same core data model as gDS V1 (tables are collections of Python lists); the syntax for defining the columns has changed. Also, referential integrity has been neatly bolted on and better (AI-generated) docs have been created - their delivery is still in flux.

---



## The concept

Imagine a spreadsheet stored entirely in Python:

- Each **column** is a Python **list** (`Name`, `Kind`, `FarmRef`, etc.).
- Every list in a table has the **same number of items**. That number is the table's row count.
- **Row 0** is the first item in every list. **Row 1** is the second item, and so on.

A **reference** (or **ref**) is a row number in a table. For example, an Animal in row `0` might have a `FarmRef` column with a value of `15`, meaning "the Animal in row `0` belongs to the Farm in row `15`." A value of `None` would mean "points nowhere."

An **index** is a Python **dictionary** that makes searching fast. For example, it can quickly find the row number of the Animal whose `Name` is `"Bessie"`.

When rows in a table get deleted, old references to that table get updated using a Reference Adjustment List (RAL) (see below).

You describe the table layout once in a `.dd` file. The compiler generates the repetitive code for you: adding rows, deleting rows, updating references, and saving the data to files as JSON. Changes to the schema are trivial to make.

There is no SQL, no database, and no code running anywhere else. Everything is just Python lists (stored in shared, global memory), row numbers, and ordinary Python functions.

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


| Keyword                                     | What it means                                          |
| ------------------------------------------- | ------------------------------------------------------ |
| `defineColumn`                              | Normal data (text, number, etc.)                       |
| `defineName`                                | The row’s name (exactly one per table)                 |
| `defineOneRef`                              | Points to one row in another table                     |
| `defineManyRefs`                            | Points to many rows in another table                   |
| `defineIndexOneRef` / `defineIndexManyRefs` | Fast lookup dictionary                                 |
| `defineRowStatus`                           | Status flag (exactly one; last line before `endTable`) |


**Naming rules** (the compiler checks these):

- Table name: no underscore — `gAnimal`, not `g_Animal`
- Column name: starts with table name + `_` — `gAnimal_Kind`
- Ref column: `{yourTable}_{otherTable}_Ref` — example: `gAnimal_gFarm_Ref`

For more detail see: [gDSCompiler-keywords-and-naming.md](gDSCompiler-keywords-and-naming.md).

### The `.py` file (the compiler writes this)

```bash
./gDSCompile mySchema.dd
```

The above CLI command creates `**mySchema.py**` next to the `.dd`. Do not edit the `.py` file by hand — compile the `.dd` file again to regenerate it.

The .py file first creates all the tables mentioned in the schema file. The tables are created in shared memory - all the processes and threads created by the application will be able to refer to the exact same table rows. The `.py` file then creates the "helper" files:


| Helper function                         | What it does                                                      |
| --------------------------------------- | ----------------------------------------------------------------- |
| `{Table}_AddARow`                       | Add one row                                                       |
| `{Table}_DeleteRows`                    | Remove rows; returns a **RAL** (see below)                        |
| `{Table}_DumpRows`                      | Print the table                                                   |
| `{Table}_WriteToFile` / `_ReadFromFile` | Save or load table data as JSON files                             |
| `{Own}_ApplyRALTo_{Dest}_Ref`           | Fix pointers in table `{Own}` after rows were deleted in `{Dest}` |


---



## Deleting rows and the Reference Adjustment List (RAL)

When you delete a row in a table, two things happen:

1. Rows below it in the table **slide up** (row 2 might become row 1).
2. References in other tables will then be referring to **old** (wrong) row numbers in the initial table.

The fix is a **RAL** (Reference Adjustment List). A RAL is a cheat sheet from `DeleteRows`. For each **old** row number it says:


| RAL value    | Meaning                                         |
| ------------ | ----------------------------------------------- |
| `None`       | That row was deleted                            |
| A number `n` | That row still exists, but it is now at row `n` |


Example — delete row 1 (`Wilbur`) from gAnimal:

```text
              Old row   Animal      RAL
                  0    'Bessie'      0
                  1    'Wilbur'   None
                  2    'Cluck'       1
```

After the delete, gAnimal has two rows. Cluck used to be at row 2; now she is row 1.

**Step 1:** Call `DeleteRows` on one table. Rows are deleted as directed and you get the RAL back.

**Step 2:** Call `ApplyRALTo_…`, with the RAL, on each table that pointed into the table with the deleted rows. That updates or clears the out-of-date pointers.

You choose **when** to run step 2 and **whether** to clear or update the old pointers. gDS does not auto-fix other tables for you.

**Delete modes:**


| Mode                     | What it deletes                     |
| ------------------------ | ----------------------------------- |
| `allRows`                | Everything                          |
| `rowStatusValueToDelete` | Rows with a certain RowStatus value |
| `rowReferencesToDelete`  | Specific row numbers you list       |


---



## Things gDS does NOT do when deleting rows in a table

- **There is no automatic “fixup across all tables.”** You first delete the rows, then apply the RAL according to the behavior you want.
- **There is no built-in locking for multiple processes.** If multiple processes share the same data, you need to define how they interact, including any locks, rules, or coordination mechanisms. One approach is very simple - run the program in **cycles**: let the multiple processes run for a while, then pause all activity except for one process, delete unnecessary rows, fix the references, and then resume activity again with multiple processes.

---



## gDSExer (the practice tool)

Run:

```bash
./gDSExer mySchema.dd
```


| You type       | What happens                                                                    |
| -------------- | ------------------------------------------------------------------------------- |
| `add`          | Add a row                                                                       |
| `delete`       | Delete rows (saves the RAL)                                                     |
| `apply`        | Fix refs using the RAL                                                          |
| `adjust`       | Change a pointer by hand                                                        |
| `dump`         | Print one table                                                                 |
| `rec` / `play` | Record or replay a script                                                       |
| `s/d`          | Save a “gold” snapshot (while recording) or compare to one (while playing back) |


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
./gDSExer mySchema.dd       # try it at the terminal
```


| Flag | Meaning                                                |
| ---- | ------------------------------------------------------ |
| `-v` | Print more messages while compiling                    |
| `-d` | Show internal schema tables (for debugging)            |
| `-O` | Use normal Python lists instead of shared-memory lists |


---



## Files in this folder


| File               | What it is                      |
| ------------------ | ------------------------------- |
| `gDSCompile`       | Run the compiler                |
| `gDSCompiler.py`   | Compiler (reads `.dd`)          |
| `gDSSchema.py`     | Checks that `.dd` is valid      |
| `gDSCompileCG.py`  | Writes the `.py` file           |
| `gDSExer`          | The practice program            |
| `gDSExerSchema.py` | Connects gDSExer to your schema |


---



## Five questions to ask yourself


| Question                         | Short answer                                                           |
| -------------------------------- | ---------------------------------------------------------------------- |
| Where is my data?                | In Python lists and dicts                                              |
| Where do I define tables?        | In the `.dd` file                                                      |
| What is a RAL?                   | A map from old row numbers to new ones after a delete                  |
| Why two steps (delete + update)? | So **you** control when and how other tables get updated               |
| What is gDSExer for?             | Learning and testing — not designing the logical structure of your app |


