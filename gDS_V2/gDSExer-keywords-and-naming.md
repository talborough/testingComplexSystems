# gDS Exerciser — Keywords and Naming Conventions

Summary of the interactive **gDSExer** command language, prompts, script format, and naming rules. The exerciser loads any compiled gDS schema (`.dd` + generated `.py`) and drives its table routines interactively or via recorded `.scr` scripts.

See also: [gDSCompiler-keywords-and-naming.md](gDSCompiler-keywords-and-naming.md) for schema (`.dd`) keywords that define the tables and routines the exerciser calls.

Note taht gDSExer *will not* help you figure out if the schema fits your application but it will help you understand the mechanics of working with the gDS code emitted by the gDSCompile routine.

---

## Invocation

```text
gDSExer SCHEMA.dd [MODULE.py]
```

| Argument    | Description |
|-------------|-------------|
| `SCHEMA.dd` | Path to the required gDS schema file. |
| `MODULE.py` | (Optional) Generated Python module. If omitted, defaults to `<schema-stem>.py` next to the `.dd` file. |

At startup the exerciser prints a one-time legend explaining prompt bracket tags (`[schema: …]`, `[exer: …]`, etc.).

---

## Main-menu commands

Entered at: `Enter a command from the above list:`

| Canonical command | Shortcuts | Purpose |
|-------------------|-----------|---------|
| `add` | `a` | Add a row to one table (`<table>_AddARow`). |
| `delete` | `d` | Delete rows in one table (`<table>_DeleteRows`); saves a **RAL**. |
| `rowstatus` | `sr` | Set `_RowStatus` on one row. |
| `apply` | `p` | Run an **ApplyRALTo** routine after a delete. |
| `adjust` | `j` | Change a ref column directly (one-ref or many-refs). |
| `dump` | `u` | Dump one table (`<table>_DumpRows`). |
| `s/d` | *(none)* | **Save** gold while recording; **diff** vs gold on playback. |
| `rec` | *(none)* | Start recording a `.scr` script (top level only). |
| `play` | *(none)* | Start playback from a `.scr` script. |
| `return` | *(none)* | Pop one script nesting level (`rec` or `play`). |
| `quit` | `q` | Exit the exerciser. |

Commands are case-insensitive. Unknown commands print usage and are not recorded. Blank main commands are ignored and do not advance recording.

Table-scoped commands (`add`, `delete`, `rowstatus`, `dump`) prompt for **table name or menu number** (1-based, schema file order).

---

## Sub-menu keywords

### DeleteRows mode (`delete` command)

| Key | Aliases | `deleteMethod` value |
|-----|---------|----------------------|
| `allRows` | `1`, `all`, `allrows` | Delete every row. |
| `rowStatusValueToDelete` | `2`, `rowstatus`, … | Delete rows with a given RowStatus. |
| `rowReferencesToDelete` | `3`, `rowrefs`, `refs`, … | Delete rows listed by row ref. |

Passed to `<table>_DeleteRows(deleteMethod, selectorValue)`.

### RAL source (`apply` command, when a saved RAL exists)

| Key | Aliases |
|-----|---------|
| `saved` | `1`, `saved`, *(empty)* |
| `build` | `2`, `build` |

### Referencing-row action (`apply`, one-ref routines)

| Key | Aliases |
|-----|---------|
| `deleteRow` | `1`, `delete`, `deleterow` |
| `setRefToNone` | `2`, `none`, `set to none`, `setrefstonone` |

### Adjust many-refs (`adjust`, many-refs column)

| Key | Aliases |
|-----|---------|
| `add` | `1`, `add` |
| `remove` | `2`, `remove` |

### Record: existing script file

| Key | Aliases |
|-----|---------|
| `overwrite` | `1`, `o`, `y`, `yes` |
| `append` | `2`, `a` |
| `cancel` | `3`, `n`, `no`, *(empty)* |

### Record: table state before recording

| Key | Aliases |
|-----|---------|
| `correct` | `1`, `ok`, `yes`, `y` |
| `playback` | `2`, `play`, `p` |
| `cancel` | `3`, `n`, `no` |

---

## Prompt conventions

Every interactive answer uses bracketed **source tags**:

| Tag | Meaning |
|-----|---------|
| `[schema: …]` | Default from the `.dd` / `<table>_AddARow` parameter default. |
| `[exer: …]` | Default defined only in gDSExer (menus, flow). |
| `[schema: required]` / `[exer: required]` | You must enter a value. |
| `[exer: !!! - to abort]` | Type `!!!` to cancel the current multi-step command. |

- **Empty line** at a prompt with a default → accept the shown default.
- **`!!!`** (`_COMMAND_CANCEL`) → abort; the current command buffer is discarded and nothing is written to the record script.

Example prompts:

```text
gAnimal_Kind [schema: None]:
Table name/number [exer: required, exer: !!! - to abort]:
Choice [exer: allRows]:
```

---

## Schema-derived naming (from the compiler)

The exerciser does not invent table API names; it binds the generated module:

| Pattern | Exerciser use |
|---------|----------------|
| `<table>_AddARow(...)` | `add` command |
| `<table>_DeleteRows(...)` | `delete` command |
| `<table>_DumpRows(...)` | `dump` command |
| `<table>_WriteToFile` / `_ReadFromFile` | Gold save/load (JSON) |
| `<owning>_ApplyRALTo_<dest>_Ref` | One-ref ApplyRALTo (`apply`) |
| `<owning>_ApplyRALTo_<dest>_Refs` | Many-refs ApplyRALTo (`apply`) |

### Ref column labels in displays and prompts

Full schema column names look like `gFarm_gAnimal_Ref`. In menus and row dumps the exerciser shows the **short label** (text after the first `_` in the owning-table prefix):

- Column `gFarm_gAnimal_Ref` → label `gAnimal_Ref`
- AddARow summary headings use `_BareName` for ordinary columns (e.g. `_Kind`) and the short ref label for refs.

### ApplyRALTo menu

Listed by generated function name, numbered **1-based**:

```text
  1 - gFarm_ApplyRALTo_gAnimal_Ref  (gFarm -> gAnimal, one-ref: …)
  2 - gHouse_ApplyRALTo_gPerson_Refs  (gHouse -> gPerson, many-refs: …)
```

### Adjust targets

Menu entries: `{table} {shortRefLabel}` (e.g. `gFarm gAnimal_Ref`), selectable by number or column name.

---

## Row and table display

**Table list header:**

```text
  Table name       Ref Contents
  ----------       --- --------
```

**Per row** (when rows exist):

```text
  gAnimal          0   Name='Bessie'  Kind='cow'  gFarm_Ref=F0 'Farm1'  RowStatus=None
```

| Field | Source |
|-------|--------|
| Row index | 0-based row number in shared storage |
| `Name=` | `defineName` column |
| Extra `Label=` | `defineColumn` bare names |
| Ref segments | Short ref label, value, dereferenced name |
| `RowStatus=` | `defineRowStatus` column |

Unresolved refs show `(???)` (e.g. `None(???)`, `2(???`).

---

## Command history

Up to **5** successful main-menu commands; shown in the **History** column beside the five-line menu (newest on the bottom line, under a centered **History** heading and 20-dash separator).

Format (semicolon-separated):

```text
command; table-or-slot-or-script; row; _Name
```

| Command | Field 2 | Field 3 | Field 4 |
|---------|---------|---------|---------|
| `add`, `delete`, `rowstatus`, `adjust`, `dump`, `apply` | Table name (or apply dest table) | Row ref if applicable | `_Name` at that row |
| `rec`, `play`, `return` | Script basename (`.scr`) | empty | empty |
| `s/d` | Gold slot (`01`, `02`, …) | empty | empty |

Example:

```text
add; gAnimal; 2; Bessie
rec; main.scr; ;
s/d; 01; ;
```

---

## Script files (`.scr`)

### Filespec

- Extension **`.scr`** is added when omitted.
- In the current directory, recorded paths prefer **basename only** (e.g. `main.scr`).
- Playback resolves numbered list entries or an existing path.

### Line types in a recorded script

| Line prefix | Meaning |
|-------------|---------|
| `# gDSExer script …` | File header (new/overwrite recordings). |
| `# PROMPT: …` | Prompt text shown to the user. |
| *(plain text)* | User answer (one line per response; blank → recorded as `None`). |
| `# OUT: …` | Mirrored terminal output for the command. |
| `# comment` + answer | Inline filespec after `rec` / `play` (no `# PROMPT:`). |

Comments and blank lines are **ignored on playback**. Only non-comment, non-blank lines supply answers, in order.

### Recording rules

- One **command buffer** per main-menu command: prompts, answers, and `# OUT:` lines are held until the command **succeeds**, then written atomically.
- **Blank or invalid** main commands: nothing written; `record_next_line_no` unchanged.
- **Main command** prompt is deferred until a non-empty command is entered.
- **`!!!`** abort: buffer discarded.

### Playback echo

```text
PLAYBACK '/path/main.scr':42 Enter a command from the above list: add
```

---

## Record / playback nesting

| Mode | Stack | Notes |
|------|-------|-------|
| Interactive | empty | Status: `INTERACTIVE` |
| Recording | `[record]` | Top-level only; `rec` while already recording is rejected. |
| Playback | `[play]` | Can nest under record or another play. |
| Record + play sub-script | `[record, play]` | Typical 2-high pattern. |

**`return`** pops the innermost level. **`return`** after the last playback level may resume a deferred `rec` (table-state prompt).

### Session status lines

```text
RECORD: '/path/main.scr' line 42
PLAYBACK: '/path/sub.scr'
```

`line` on `RECORD:` is the next line number to be written in the `.scr` file.

The menu + History column and status print once immediately before each main command prompt (interactive/recording) or before each playback main-command echo.

---

## Gold files (`s/d`)

Gold snapshots belong to the **outermost** (gold-owner) script session.

| Name | Pattern |
|------|---------|
| Gold root directory | `{script_basename}_gold/` |
| Slot folder | `{script_basename}_gold/01/`, `02/`, … (two digits, per session counter) |
| Table JSON | `{script_basename}_gold/NN/{table}.json` |
| Diff test output | `tempTables/{table}.json` |

- **While recording:** `s/d` **saves** all tables to the next slot.
- **While playing back:** `s/d` **diffs** current tables against that slot; loops until PASS or user abort.

History field 2 for `s/d` is the slot number (`01`, `02`, …).

---

## RAL (Reference Adjustment List) naming

| Symbol | Meaning |
|--------|---------|
| `SAVED_RALS[table]` | RAL list from the most recent successful `delete` on that table |
| `APPLY_RAL_COMPLETED` | Set of `<owning>_ApplyRALTo_<dest>_Ref\|_Refs` names already run for current RAL(s) |

After a new delete on a table, ApplyRALTo routines targeting that table are marked pending again. The saved-RAL display shows `[x]` / `[ ]` for done vs pending ApplyRALTo routines.

---

## Outcome display

Successful operations print a banner:

```text
***************
Created gAnimal row 2: _Name='Bessie'  _Kind='cow'  …
***************
```

Then `Press Return to continue…` before the table redisplay.

---

## Quick workflow example

```text
rec main.scr          → record controlling script
play create3.scr      → nested playback while recording
return                → end nested play
add                   → gAnimal, fill AddARow prompts
s/d                   → save gold slot 01
return                → stop recording
play main.scr         → playback; s/d diffs at each checkpoint
quit
```
