# animalFarm_02

## What is this?

**animalFarm_02** is a computer program that pretends to run several farms at once. Each farm has cows and chickens. Background workers can **tend** animals (milk cows, collect eggs) or **raise** animals (add new ones or remove old ones).

The program is really a **practice lab** for testing complicated software. Many things happen at the same time, and the program checks whether all the numbers still add up correctly. If they do not, it stops with an error.

Think of it like a video game where you are the manager—but the goal is to stress-test the system and catch operating and counting mistakes.

## Before you start

You need:

- **Python 3** installed on your Linux computer
- The file **`animalFarm_02.py`** in the same folder as `animalFarm_02`

If `animalFarm_02.py` is missing or out of date, generate it from the schema file:

```bash
../gDS_V2/gDSCompile animalFarm_02.dd
```

(Use the `gDSCompile` tool from your gDS installation; the exact path may differ on your machine.)

Make the program executable (once):

```bash
chmod +x animalFarm_02
```

## How to run it

### Interactive mode (you type commands)

```bash
./animalFarm_02
```

The program builds 3 counties, 9 farms, and 54 animals (over the course of about 10 seconds). Then it shows a live screen and waits for you to type commands.

To leave the program, press **Ctrl+C**.

### Batch mode (one automatic test run)

```bash
./animalFarm_02 --rt=45 --ct=15 --tc=3 --tx=3 --rc=3 --rx=3
```

| Option | Meaning |
|--------|---------|
| `--rt=45` | Total run time in seconds |
| `--ct=15` | How long each cycle runs before checking the numbers |
| `--tc=3` | Number of cow-tending workers |
| `--tx=3` | Number of chicken-tending workers |
| `--rc=3` | Number of cow-raising workers |
| `--rx=3` | Number of chicken-raising workers |

In batch mode the screen still updates, but you cannot type commands—the run plays out by itself.

For full built-in help:

```bash
./animalFarm_02 --help
```

## Reading the screen

The display refreshes while you work. Important parts:

- **Farm summary** — each row shows a farm’s cow count, chicken count, busy animals, new milk/eggs, and totals.
- **Red numbers** — something is active or needs attention (for example, animals being worked on).
- **Calculated vs observed** — two independent ways of counting animals, milk, and eggs. They should match after you run maintenance commands (see below).

Switch views:

| Command | What it does |
|---------|----------------|
| `fs` | Farm summary table |
| `ad` | One character per animal (`c` = cow, `x` = chicken) |

## Commands (interactive mode)

Type a short code and press **Enter**.

### Displays and info

| Command | What it does |
|---------|----------------|
| `fs` | Show farm summary |
| `ad` | Show animal detail |
| `dc` | Dump county data to the screen |
| `df` | Dump farm data to the screen |
| `da` | Dump animal data to the screen |
| `help` | Show longer help text |

### Start and stop workers

| Command | What it does |
|---------|----------------|
| `tc` | Start cow-tending workers (milk cows) |
| `tx` | Start chicken-tending workers (gather eggs) |
| `rc` | Start cow-raising workers (add/remove cows) |
| `rx` | Start chicken-raising workers (add/remove chickens) |
| `eb` | End all background workers |

When you start `tc`, `tx`, `rc`, or `rx`, the program asks how many parallel workers you want (default is 3).

### Maintenance and checking

| Command | What it does |
|---------|----------------|
| `up` | Move milk/egg totals from animals onto farms, then zero the animals’ counters |
| `ca` | Remove “erased” animals from the database |
| `va` | Run `up`, then `ca`, then verify all counts match |
| `e1` | Deliberately break a count (for testing error handling) |

Run `up` and `ca` (or just `va`) **only when no background workers are running** (`eb` first if needed).

### Test run (interactive)

| Command | What it does |
|---------|----------------|
| `st` | Start a timed test run: you pick worker counts, run time, and cycle time |

A **test run** keeps workers going for a while, stops them each **cycle**, checks the numbers, then starts another cycle until the total **run time** is up.

## How the counting works

The program tracks three things two different ways:

1. **Animals** — how many exist
2. **Milk** — how much cows produce
3. **Eggs** — how many chickens lay

- **Calculated** — a running total updated whenever a worker creates, deletes, or produces something.
- **Observed** — totals rebuilt from the farm and animal tables.

At the end of a cycle (or when you type `va`), the program saves data to files, reloads it, rolls up production, cleans up erased animals, and compares calculated vs observed. If anything disagrees, you see:

```text
The counts above don't match!!!
```

and the program exits. If everything agrees, you see:

```text
The counts above match!!!
```

## Typical workflow

1. Start the program: `./animalFarm_02`
2. Watch the farm summary (`fs` is the default).
3. Start some workers, for example: `tc`, then `3` when asked.
4. When you want to stop: `eb`
5. Check the data: `va`
6. Or run a full timed test: `st` and follow the prompts.

## Files you might notice

| File | Purpose |
|------|---------|
| `animalFarm_02` | Main program |
| `animalFarm_02.dd` | Data definition (schema) |
| `animalFarm_02.py` | Generated database support code |
| `county_table.json` | Saved county data (created during verification) |
| `farm_table.json` | Saved farm data |
| `animal_table.json` | Saved animal data |

## More background

This program demonstrates ideas used when testing large, busy systems. For more context, see [TestingComplexSystems.com](https://TestingComplexSystems.com).
