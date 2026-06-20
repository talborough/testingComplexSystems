# gDS V2 — Compiler and Exerciser

First "look see" of the V2 compiler and exerciser. Testing and updating the case studies is underway.

Tools for defining gDS schemas (`.dd` files), compiling them to Python, and interactively exercising the generated tables.

V2 of gDS maintains the central core of gDS V1: table columns are made up of collections of Python "list"s defined in global shared memory, one list per table column. However the makeup of the schema (.dd) file has changed, the naming conventions have changed, referential integrity has been added, helper routines have changed and an "exerciser" gDSExer has been made available.

Note that gDSExer *will not* help you figure out if the schema fits your application but it will help you understand the mechanics of working with the gDS code emitted by the gDSCompile routine.

## Components

| Tool | Purpose |
|------|---------|
| **gDSCompile** | Compile a `.dd` schema to a generated `.py` module |
| **gDSExer** | Interactive exerciser / test harness for any compiled schema |

## Quick start

### Compile a schema

```bash
./gDSCompile mySchema.dd
```

Output: `mySchema.py` beside the `.dd` file.

Options:

| Flag | Effect |
|------|--------|
| `-v` | Verbose phase/verify/generate messages |
| `-d` | Dump IR (`dsTable` / `dsVariable`) after load |
| `-O` | Generated `.py` uses ordinary `[]` / `{}` instead of `multiprocessing.Manager` |

### Run the exerciser

```bash
./gDSExer mySchema.dd
# or explicitly:
./gDSExer mySchema.dd mySchema.py
```

From the main menu you can add/delete rows, apply RAL updates, adjust refs, dump tables, save/diff gold snapshots, and record or play back `.scr` scripts.

## Documentation

| Document | Contents |
|----------|----------|
| [gDSCompiler-keywords-and-naming.md](gDSCompiler-keywords-and-naming.md) | Schema keywords (`defineTable`, `defineOneRef`, …), naming rules, generated routine names |
| [gDSExer-keywords-and-naming.md](gDSExer-keywords-and-naming.md) | Exerciser commands, prompts, `.scr` format, gold files, history column |

## Typical workflow

1. Write or edit a `.dd` schema.
2. `./gDSCompile schema.dd`
3. `./gDSExer schema.dd` — interactively build table state, or record sub-scripts and a controlling script.
4. Use **s/d** during recording to save gold snapshots; play back the script and **s/d** diffs against gold at each checkpoint.

## Bootstrap

To rebuild the compiler's own IR module:

```bash
./gDSCompile -O gDSIr.dd
```

(`-O` is applied automatically for the processor schema `gDSIr.dd`.)
