# nfsTest

**A hands-on lab for testing shared folders across Linux computers**

This project is part of [Case Study 3](https://TestingComplexSystems.com) from TestingComplexSystems.com. It is meant for learning how complex computer systems behave when things go wrong — not for everyday file sharing.

This has *not* been converted to use gDS V2 yet!

---

## What is this?

Imagine you have several Linux computers on a network. One computer **shares** a folder, and the others **use** that folder as if it were on their own machine. That sharing system is called **NFS** (Network File System).

**nfsTest** is a program that:

1. Sets up NFS sharing between multiple computers (called **hosts**)
2. Starts programs that **read and write files** on those shared folders
3. Lets you **stress-test** the setup — reboot a computer, swap roles, pause work, and more
4. **Checks** that data stays correct and reports problems if something breaks

Think of it like a science experiment: you build a small network, run workloads on it, poke at it, and watch what happens.

---

## The computers involved

| Role | What it does |
|------|----------------|
| **Control host** | The computer where you run `./nfsTest`. It sends commands to the others over SSH (secure remote login). |
| **Server host(s)** | Share folders over NFS so other computers can use them. |
| **Client host(s)** | Connect to shared folders and run read/write tests on them. |

You need at least **one server** and **one client**, plus the control host (often the same machine you use to run nfsTest).

---

## Files in this folder

| File | What it is |
|------|------------|
| `nfsTest` | The main program — menu, setup, and test control |
| `nfsTest.conf` | Your settings (created on first run — see below) |
| `nfsTest.dd` | Data definitions used to build internal tables |
| `nfsTest.py` | Generated code from `nfsTest.dd` (you do not edit this by hand) |
| `ioEngine` | Writes and reads test files on a shared folder; checks for errors |
| `appendALine` / `removeALine` | Small helpers used during NFS setup on remote hosts |
| `One.scr` | Example script that runs a sequence of commands automatically |

---

## What you need before starting

### Software (on the control host)

- **Linux** (Ubuntu works well)
- **Python 3**
- **Paramiko** (Python SSH library):

  ```bash
  sudo apt install python3-paramiko
  ```

### Test computers (VMs or real machines)

Each test host should:

1. Run Linux (Ubuntu is fine)
2. Be reachable from the control host (ping works)
3. Have **SSH server** installed:

   ```bash
   sudo apt update
   sudo apt install openssh-server
   sudo systemctl status ssh
   ```

4. Use the **same username and password** on all machines (with `sudo` access). nfsTest uses password login, not SSH keys.

### Build step (one time)

nfsTest needs a generated file called `nfsTest.py`. From this directory, run:

```bash
../gDS/gDSCodeGen nfsTest
```

That reads `nfsTest.dd` and creates `nfsTest.py`. If `nfsTest.py` is missing or older than `nfsTest.dd`, nfsTest will exit and tell you to run this command.

---

## First-time setup

### Step 1: Run nfsTest once to create the config file

```bash
chmod +x nfsTest ioEngine appendALine removeALine
./nfsTest
```

The program creates **`nfsTest.conf`** and exits. Open that file in a text editor.

### Step 2: Edit `nfsTest.conf`

Fill in your real values. Example:

```ini
username = myuser
password = mypassword

serverCount = 1
clientCount = 2

exportFSPerHost = 2
fsUserPerImportFS = 3

testhostIdentifier = 192.168.1.101
testhostIdentifier = 192.168.1.102
testhostIdentifier = 192.168.1.103
```

| Setting | Meaning (in plain English) |
|---------|----------------------------|
| `username` / `password` | Login used on every host |
| `serverCount` | How many hosts act as NFS servers |
| `clientCount` | How many hosts act as NFS clients |
| `exportFSPerHost` | Max shared folders per server host |
| `fsUserPerImportFS` | Max read/write workers per mounted share |
| `testhostIdentifier` | IP address or hostname of each test machine (need at least `serverCount + clientCount` entries) |

Save the file, then run nfsTest again:

```bash
./nfsTest
```

It will ping each host, connect over SSH, and show a live status screen.

---

## Using the program

### The main screen

After startup you see a dashboard with host states, counters, and a command prompt. Press **Enter** with no command to show or hide the help menu.

On first run, nfsTest may ask if you want to:

- **`cleanall`** — reset and install software on test hosts
- **`ss`** — start state machine threads (prepare the test platform)
- **`aa`** — activate everything (start NFS sharing and I/O)

You can also type these commands yourself at the prompt.

### Common commands

| Command | What it does |
|---------|--------------|
| `help` | Show help (same as toggling with Enter) |
| `insw` | Install needed packages on test hosts |
| `cleanall` | Clean up and reinstall on test hosts |
| `ss` | **S**tart **s**tate machines (setup threads) |
| `aa` | **A**ctivate **a**ll resources |
| `dea n` | Deactivate host number `n` |
| `acts n` / `actc n` | Activate host `n` as server or client |
| `rh n` | Reboot host `n` |
| `pau n` / `res n` | Pause or resume host `n` |
| `waa n` / `wai n` | Wait until host `n` is Active or Inactive |
| `wait 5` | Wait 5 seconds |
| `script One` | Run commands from `One.scr` |
| `dhr` / `der` / `dir` / `dur` | Dump table rows (hosts, exports, imports, users) |

Host numbers are shown on the status display (host #0, #1, …).

### Example workflow (manual)

1. `./nfsTest`
2. `cleanall` — prepare hosts
3. `ss` — start threads
4. `aa` — turn everything on; I/O should begin
5. Try `rh 1` to reboot a host and watch the counters
6. Use `dea 2` then `actc 2` to deactivate and reactivate a client

### Example workflow (script)

The file `One.scr` runs a fixed sequence:

```text
cleanall
ss
aa
waa 0
...
dea 2
actc 2
```

Run it with:

```text
script One
```

---

## How it works (simple version)

nfsTest does not create and destroy things on the fly during a test. Instead, it **builds the biggest system you configured up front**, then turns pieces on and off using **state machines**.

Each important piece (host, shared folder, mounted folder, read/write worker) has a **state**, such as:

`Inactive` → `Activating` → `Active` → `Pausing` → `Paused` → …

When a read/write worker is **Active**, nfsTest runs **`ioEngine`** on that host. ioEngine creates a file, writes patterned data, reads it back, and verifies the bytes match. If something is wrong (I/O error, corrupted data, missing file), the test platform stops.

**What nfsTest is checking:**

- If a **server** reboots, clients should keep working (or recover correctly).
- If a **client** reboots, its workloads stop and must be handled properly when it comes back.
- Shared data should stay consistent across the network.

Logs are written to **`nfsTest.log`** in the same directory.

---

## Troubleshooting

| Problem | Things to try |
|---------|----------------|
| `./nfsTest.py does not exist` | Run `../gDS/gDSCodeGen nfsTest` |
| Program exits after creating `nfsTest.conf` | Edit the config file, then run `./nfsTest` again |
| Cannot connect to a host | Check SSH is running, IP is correct, username/password match |
| Ping fails | Fix networking between control host and test hosts first |
| Test stops with an error | Check `nfsTest.log` and the on-screen counters (bad connections, data compare errors, etc.) |
| Stops after 30 minutes | Built-in limit to avoid filling disk; restart if you need a longer run |

For more detail, run:

```bash
./nfsTest --help
```

Or read the documentation at the bottom of the `nfsTest` source file.

---

## Big picture

nfsTest is a **learning tool** for understanding:

- How **NFS** shares storage across machines
- How **remote commands** (SSH) control many computers from one place
- How **state machines** manage complex systems that grow and shrink
- What happens when parts of a system **fail or restart**

You do not need to understand every line of code to run experiments. Start with a small setup (1 server, 1–2 clients), run `cleanall`, `ss`, and `aa`, then try rebooting a host and watching the display.

---

## Quick reference

```bash
# One-time build
../gDS/gDSCodeGen nfsTest

# First run (creates config)
./nfsTest

# Edit nfsTest.conf, then:
./nfsTest

# Help
./nfsTest --help
```

**Related site:** [TestingComplexSystems.com](https://TestingComplexSystems.com)
