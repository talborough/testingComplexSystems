# What is `PVHTSG.dd`?

This file is a **blueprint** for how to store information about people, vehicles, houses, towns, states, and governors. You do not run the `.dd` file directly. A tool called **gDSCompile** reads it and builds a Python file (`PVHTSG.py`) that your program can actually use.

Think of it like an architect’s floor plan: the `.dd` file describes the layout; the Python file is the finished building.

---

## The name: PVHTSG

The letters stand for the main things this database tracks:


| Letter | Meaning  |
| ------ | -------- |
| **P**  | Person   |
| **V**  | Vehicle  |
| **H**  | House    |
| **T**  | Town     |
| **S**  | State    |
| **G**  | Governor |


So **PVHTSG** = Person, Vehicle, House, Town, State, Governor.

---

## Big idea: tables and rows

If you have used a spreadsheet, you already know the idea.

- A **table** is like one sheet (for example, “People” or “Vehicles”).
- A **row** is one record on that sheet (one person, one car, one house).
- A **column** is one kind of fact (name, birthday, address).

The `.dd` file says which tables exist, which columns each table has, and how tables link to each other.

---

## How the tables connect

Here is the story the data tells, from small pieces up to the big picture:

```
Person  ──lives in──►  House  ──located in──►  Town  ──part of──►  State
   │                                                      ▲
   └──owns (can be many)──►  Vehicle                      │
                                                          │
Governor term  ──connects──►  Person + State  ────────────┘
```

- A **person** can live in one **house** and own many **vehicles**.
- A **house** sits in one **town**.
- A **town** belongs to one **state**.
- A **governor term** records which **person** was governor of which **state**, and for which years.

---

## The six tables

### 1. `gPerson` — People


| Column             | What it stores               |
| ------------------ | ---------------------------- |
| Name               | Person’s name (required)     |
| DOB                | Date of birth                |
| House reference    | Which house they live in     |
| Vehicle references | List of cars they own        |
| Gender             | Optional                     |
| Row status         | Internal flag (often unused) |


### 2. `gVehicle` — Vehicles


| Column | What it stores                     |
| ------ | ---------------------------------- |
| Name   | Optional label                     |
| Year   | Model year                         |
| Type   | Kind of vehicle (car, truck, etc.) |
| VIN    | Vehicle ID number                  |


There is also an **index** on vehicle type so you can quickly find all vehicles of a given type.

### 3. `gHouse` — Houses


| Column         | What it stores             |
| -------------- | -------------------------- |
| Address        | Street address             |
| Town reference | Which town the house is in |


### 4. `gTown` — Towns


| Column          | What it stores             |
| --------------- | -------------------------- |
| Name            | Town name                  |
| Zip code        | Postal code                |
| State reference | Which state the town is in |


### 5. `gState` — States


| Column | What it stores        |
| ------ | --------------------- |
| Name   | State name (required) |


There is an **index** on state name so you can look up a state by name quickly.

### 6. `gGovTerm` — Governor terms


| Column           | What it stores      |
| ---------------- | ------------------- |
| State reference  | Which state         |
| Person reference | Who was governor    |
| Start year       | When the term began |
| End year         | When the term ended |


---

## Special words in the `.dd` file

These are the main commands. Lines starting with `#` are comments (notes for humans).


| Command               | Plain English                                                                                               |
| --------------------- | ----------------------------------------------------------------------------------------------------------- |
| `defineTable`         | Start a new table.                                                                                          |
| `endTable`            | Finish that table.                                                                                          |
| `defineName`          | The main name field for a row. If there is no default value, you **must** provide a name when adding a row. |
| `defineColumn`        | A regular piece of data (text, number, date, etc.).                                                         |
| `defineOneRef`        | A link to **one** row in another table (like “this house is in town #3”).                                   |
| `defineManyRefs`      | Links to **many** rows in another table (like “this person owns cars #1, #4, and #7”).                      |
| `defineIndexOneRef`   | A fast lookup: given a value (like a state name), find the matching row.                                    |
| `defineIndexManyRefs` | A fast lookup: given a value (like vehicle type), find **all** matching rows.                               |
| `defineRowStatus`     | An extra column used internally; often left as `None`.                                                      |
| `None` (as a default) | This field is optional — you can skip it.                                                                   |


---

## What is a “reference”?

A reference is not the full object stored twice. It is a **pointer** — a row number that says “go look in the other table.”

Example:

- Row 0 in `gPerson` might have `gPerson_gHouse_Ref = 2`
- That means: “this person lives in row 2 of the `gHouse` table”
- To get the address, you look up row 2 in `gHouse`

This is how relational databases avoid repeating the same address on every person who lives there.

---

## Example: reading one table block

```text
defineTable     gPerson
defineName      gPerson_Name
defineColumn    gPerson_DOB
defineOneRef    gPerson_gHouse_Ref  gHouse      None
defineManyRefs  gPerson_gVehicle_Refs           gVehicle
defineColumn    gPerson_Gender                  None
defineRowStatus gPerson_RowStatus               None
endTable
```

In plain language:

1. Create a table called `gPerson`.
2. Every person needs a name.
3. Store their birthday.
4. Link to one house (optional, because of `None`).
5. Link to zero or more vehicles.
6. Gender is optional.
7. Row status is optional.
8. Done with this table.

---

## What happens after you write the `.dd` file?

1. You run **gDSCompile** on `PVHTSG.dd`.
2. It generates `**PVHTSG.py`** — Python code with lists for each column and helper functions such as:
  - `gPerson_AddARow(...)` — add a new person
  - `gPerson_DumpRows()` — print all people
  - `gPerson_WriteToFile(...)` / `gPerson_ReadFromFile(...)` — save and load data as JSON
3. Your program imports that file:
  ```python
   from PVHTSG import *
  ```

You edit the `**.dd` file** when you want to change the design. You use the `**.py` file** when you want to add or read data.

---

## Why use a `.dd` file instead of writing Python by hand?

- **One place to design** — all tables and links are visible in one short file.
- **Fewer mistakes** — the compiler generates matching add, delete, save, and load code for every table.
- **Easier to change** — add a column in the `.dd` file, recompile, and the Python updates consistently.

---

## Quick summary


| File         | Role                                              |
| ------------ | ------------------------------------------------- |
| `PVHTSG.dd`  | Blueprint: what tables exist and how they connect |
| `PVHTSG.py`  | Working code: lists, add-row functions, save/load |
| Your program | Imports `PVHTSG.py` and stores real data          |


The `.dd` file is not a program. It is a **recipe** that tells gDSCompile how to build a small database for people, vehicles, houses, towns, states, and governors.