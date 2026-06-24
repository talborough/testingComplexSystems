# Animal Farm Case Study

[This program uses gDS_V2.]

Imagine you are running a computer simulation of farms. Counties contain farms, farms contain animals, and many workers might try to add animals at the same time. This project shows how programmers organize that kind of information and keep it safe when lots of things happen at once.

Data is stored **in memory** using a tool called **gDS** (global Data Store).

---

## The story in plain English

Picture a map:

```
County A                    County B
  └── Farm A                  ├── Farm B
                              └── Farm C
```

- A **county** is a big area (like "County A").
- A **farm** belongs to one county (like "Farm B" in "County B").
- An **animal** belongs to one farm (like "Chicken #03" on "Farm C").

When the program runs, it:

1. Creates 2 counties and 3 farms.
2. Starts many small jobs that each add one animal (cows and chickens).
3. Shows you everything that was stored.
4. Lets you search—for example, "show me all chickens in County B."
5. Lets you look up one animal by its ID number.

---

## How the data is organized (tables)

Programmers often store related information in **tables**, like spreadsheets.

### County table (`gCounty`)

| Row # | County name |
|-------|-------------|
| 0     | County A    |
| 1     | County B    |

### Farm table (`gFarm`)

| Row # | Farm name | County (row #) |
|-------|-----------|----------------|
| 0     | Farm A    | 0              |
| 1     | Farm B    | 1              |
| 2     | Farm C    | 1              |

### Animal table (`gAnimal`)

| Row # | Animal type | Animal name   | Farm (row #) |
|-------|-------------|---------------|--------------|
| 0     | Cow         | Cow #01       | 0            |
| 1     | Chicken     | Chicken #01   | 1            |
| ...   | ...         | ...           | ...          |

Each row gets a **row reference** (row number), starting at 0. Other tables use that number to point at related rows—like writing "see row 1" instead of copying the whole farm name everywhere.

---

## Files in this project

| File | What it is |
|------|------------|
| `animalFarm_01.dd` | The **blueprint**. Describes the tables and columns. Not Python — you do not run this file directly. |
| `animalFarm_01.py` | The **data layer**. Created automatically from the blueprint by a tool called `gDSCompile`. Holds the tables and helper functions like `gCounty_AddARow`. |
| `animalFarm_01` | The **main program**. The demo you actually run. It creates counties and farms, starts workers, and prints results. |

**How `animalFarm_01.py` is born:**

```
animalFarm_01.dd  →  gDSCompile  →  animalFarm_01.py
   (blueprint)        (tool)         (Python code)
```

If `animalFarm_01.py` is missing or older than `animalFarm_01.dd`, the main program will stop and tell you to run the code generator first.

---

## gDS — data in shared memory

- Data lives **in the computer’s RAM** while the program runs.
- When the program ends, that in-memory data is gone (unless you save it to a JSON file).
- Good for learning and for programs where everything runs in one session.

Think of it like a shared whiteboard everyone reads and writes on during class. When class ends, the whiteboard gets erased.

The program still uses the same core ideas: tables, row numbers, and links between counties → farms → animals.

---

## Many workers at once (concurrency)

The demo does something realistic: **39 jobs** run at roughly the same time to add animals.

- **9 processes** add cows (heavier, separate workers).
- **30 threads** add chickens (lighter workers inside one process).

If two workers tried to add an animal to the same table *at the exact same moment* without rules, data could get corrupted. To prevent that, the program uses a system **lock** (`MasterLock`):

1. A worker says “I need the table.”
2. Only that worker can add a row until it is done.
3. Then the next worker gets a turn.

It is like one person holding the bathroom key—only one person inside at a time, but everyone eventually gets in.

---

## What happens when you run the program

The demo follows this script:

1. **Setup** — Add County A, County B, and three farms.
2. **Press Enter** — Start adding animals with random delays (2–8 seconds each), so they finish in unpredictable order.
3. **Wait** — All 39 workers finish.
4. **Press Enter** — Print the county table, then farms, then animals.
5. **Search** — List every chicken in County B.
6. **Loop** — Type an animal’s row number to see that animal, its farm, and its county.

---

## How to run

You need **Python 3** installed.

First, make sure `animalFarm_01.py` exists (generate it if your instructor told you to):

```bash
../gDS/gDSCompile animalFarm_01
```

Then run:

```bash
./animalFarm_01
```

---

## Big ideas you can take away

1. **Structure data in tables** — Rows and columns keep information neat and easy to search.
2. **Use references instead of copies** — A farm stores “county row 1,” not a duplicate of every county detail.
3. **Separate blueprint from code** — `.dd` files describe *what* you store; `.py` files implement *how*.
4. **Use memory when it fits** — gDS keeps data in RAM for fast, temporary work during a program run.
5. **Protect shared data** — Locks matter when many workers touch the same tables.

---

## Quick glossary

| Term | Simple meaning |
|------|----------------|
| **Table** | A grid of related information (like a spreadsheet page). |
| **Row** | One record in a table (one county, one farm, or one animal). |
| **Row reference** | The row’s ID number, used to link tables together. |
| **gDS** | A system that keeps tables in memory and generates Python code from a `.dd` blueprint. |
| **Process** | A separate running copy of work (like opening a second app). |
| **Thread** | A lighter worker inside the same program. |
| **Lock** | A rule that only one worker can change shared data at a time. |

---

## About this case study

This project is a teaching example. It is small on purpose—you can see every table, every link, and every worker— but it uses the same patterns found in real software: organized data, generated data layers, and safe concurrent updates.

If something confuses you, trace one chicken from start to finish: find its row in `gAnimal`, follow the farm row number to `gFarm`, then follow the county row number to `gCounty`. That one path is the whole design in miniature.
