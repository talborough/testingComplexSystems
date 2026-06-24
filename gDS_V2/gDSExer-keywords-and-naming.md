# gDS Exerciser — Command Guide

**gDSExer** is a terminal program that lets you try your compiled tables without writing a full app. You type short commands (`add`, `delete`, …), answer questions, and see the tables update on screen.

It uses the same Python code your real program would use.

Schema language (`.dd` file): [gDSCompiler-keywords-and-naming.md](gDSCompiler-keywords-and-naming.md).

**Remember:** gDSExer tests whether the **code works**. It does not tell you if your table design is right for your application.

---

## How to start

```bash
./gDSExer mySchema.dd
```

When you run it, it starts by explaining the text found in the square brackets at prompts, like `[schema: None]`.

---

## Main commands

When you see `Enter a command from the above list:`, type one of these (shortcuts in parentheses):

### Work on tables


| Type            | Shortcut | What it does                                |
| --------------- | -------- | ------------------------------------------- |
| `add`           | `a`      | Add a new row to a table                    |
| `delete`        | `d`      | Remove rows from a table                    |
| `set rowstatus` | `sr`     | Change the RowStatus on one row             |
| `apply`         | `p`      | Fix pointers in other tables after a delete |
| `adjust`        | `j`      | Change a pointer by hand                    |
| `dump`          | `u`      | Print one table                             |


For `add`, `delete`, `rowstatus`, and `dump`, you then pick a table by **name** or **number** from the menu.

### Scripts and testing

You can test ad-hoc, interactively and also record your inputs to gDSExer and play them back later. You can take checkpoints as you record and on subsequent replays, check your progress against the saved gold files.

Here are the commands involved in recording and playback:

| Type     | Shortcut | What it does                                                                            |
| -------- | -------- | --------------------------------------------------------------------------------------- |
| `rec`    | —        | Start recording everything you type to a `.scr` file                                    |
| `play`   | —        | Run a saved `.scr` file                                                                 |
| `return` | —        | Go back one level (stop inner script)                                                   |
| `s/d`    | —        | **While recording:** save a snapshot. **While playing back:** compare to saved snapshot |
| `quit`   | `q`      | Exit                                                                                    |


Commands are not case-sensitive. A blank line at the main menu does nothing. A wrong command shows help and is not recorded.

---

## Understanding prompts

```text
gAnimal_Kind [schema: None]:
```


| Text in brackets         | Meaning                      |
| ------------------------ | ---------------------------- |
| `[schema: …]`            | Default from your `.dd` file |
| `[exer: …]`              | Default from gDSExer         |
| `[schema: required]`     | You must type something      |
| `[exer: !!! - to abort]` | Type `!!!` to cancel         |


- Press **Enter** on an empty line to accept the default.
- Type `**!!!`** to cancel the whole command (nothing saved to the script).

---

## What you see on screen

**Tables** (one line per row):

```text
  Table name       Ref Contents
  ----------       --- --------
  gAnimal          0   Name='Bessie'  Kind='cow'  gFarm_Ref='Farm1'  RowStatus=None
```

- The number after the table name is the **row index** (starts at 0).
- Pointers show the other row’s name when possible.
- `(???)` means a bad or missing pointer.

**History** (five lines on the right of the menu) — your last commands, newest at the bottom.

**Status lines** — tell you if you are recording or playing a script:

```text
RECORD: '/path/main.scr' line 42
PLAYBACK: '/path/sub.scr'
```

---

## Scripts (`.scr` files)

When you `rec`, your answers are saved to a `.scr` file. When you `play`, gDSExer reads that file instead of waiting for you to type.

A script line can be:


| Line starts with   | Meaning                      |
| ------------------ | ---------------------------- |
| `# gDSExer script` | Header                       |
| `# PROMPT:`        | The question that was asked  |
| (normal text)      | Your answer                  |
| `# OUT:`           | Text that appeared on screen |


Only your answers are replayed. Comments are skipped.

You can **nest** scripts: record a main script, `play` a smaller script inside it, then `return` to go back.

---

## Gold snapshots (`s/d`)

A **gold** snapshot is a saved copy of all your tables at one moment — used to check nothing changed later.

While **recording**, `s/d` saves to folders like `myScript_gold/01/`, `02/`, …

While **playing back**, `s/d` compares live tables to that snapshot. You get **PASS** or **FAIL**.

---

## Typical `delete` then `apply` flow

1. `delete` — remove rows from a table (RAL is saved).
2. `apply` — fix pointers in other tables that pointed at deleted rows. You may need to run `apply` more than once if several tables had pointers.
3. `dump` or `s/d` — check the result.

The screen shows `[x]` or `[ ]` next to each apply step so you know what is done.

---

## Example session

```text
rec main.scr       # start recording
play setup.scr     # run a helper script inside the recording
return             # done with helper script
add                # add an animal (answer the prompts)
s/d                # save gold snapshot #01
return             # stop recording
(Restart gDSExer)
play main.scr      # run it again; s/d checks gold at each checkpoint
quit
```

After each good command you see a short message, press Enter, then all table rows print again.