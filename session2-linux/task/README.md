# Session 2 — Linux — Tasks

- **Name:** Raj Prakash
- **Enrollment No:** 24BCS10328

> **Status:** done
>
> My machine is a Mac (Apple Silicon), so there is no `useradd`, no `/etc/passwd` in the
> Linux sense and no `ls -li` inode semantics to demonstrate. I ran everything in an
> **Ubuntu 24.04.4 LTS** container on Docker Desktop instead — kernel
> `6.12.76-linuxkit aarch64`, hostname `linux-lab`:
>
> ```bash
> docker run -d --name linux-lab --hostname linux-lab ubuntu:24.04 sleep infinity
> docker exec -it linux-lab bash
> ```
>
> That is real Linux running a real kernel, so the inode and user-management behaviour
> below is genuine, not simulated.

---

## Task 1: Hard links vs soft links

### What the task asked

Explain hard links and symbolic links, create one of each, compare their inode numbers,
then delete the original file and see what happens to each link.

### Commands

```bash
mkdir -p /root/session2-task && cd /root/session2-task
echo 'This is the original file content.' > file1.txt
ln    file1.txt hardlink.txt      # hard link
ln -s file1.txt softlink.txt      # soft link (symbolic)
```

### Output

![Hard link vs soft link demonstration](screenshots/task1-links.png)

Before deleting anything:

```text
$ ls -li
total 8
1385031 -rw-r--r-- 2 root root 35 Sep  4 19:56 file1.txt
1385031 -rw-r--r-- 2 root root 35 Sep  4 19:56 hardlink.txt
1385032 lrwxrwxrwx 1 root root  9 Sep  4 19:56 softlink.txt -> file1.txt

$ stat -c '%-14n inode=%-8i links=%h  type=%F' file1.txt hardlink.txt softlink.txt
file1.txt      inode=1385031  links=2  type=regular file
hardlink.txt   inode=1385031  links=2  type=regular file
softlink.txt   inode=1385032  links=1  type=symbolic link
```

Three things to read off this:

- `file1.txt` and `hardlink.txt` both sit on **inode 1385031** and both report a link count
  of **2**. They are not an original and a copy — they are two directory entries pointing
  at one inode. Neither is "the real one".
- `softlink.txt` has **its own inode (1385032)** and a link count of 1. It is a separate
  file.
- The symlink's size is **9 bytes**, which is exactly `len("file1.txt")`. That is the whole
  content of a symlink: the target path as text. It stores a name, not a reference to data.

### Now delete the original

```text
$ rm file1.txt && ls -li
total 4
1385031 -rw-r--r-- 1 root root 35 Sep  4 19:56 hardlink.txt
1385032 lrwxrwxrwx 1 root root  9 Sep  4 19:56 softlink.txt -> file1.txt

$ cat hardlink.txt
This is the original file content.

$ cat softlink.txt; echo "exit=$?"
cat: softlink.txt: No such file or directory
exit=1
```

The hard link's count went **2 → 1** and the data is still readable. The symlink still
exists as a file — `ls` lists it fine — but it now points at a name nothing answers to. A
dangling symlink.

The interesting part is what this says about `rm`. It did not "delete the file". It removed
one directory entry and decremented the inode's link count. The data blocks are only freed
when that count hits zero, which is why `hardlink.txt` still works. `file1.txt` was never
the file; it was one of the file's two names.

### Comparison

| | Hard link | Soft link |
|---|---|---|
| Points at | the **inode** | a **path string** |
| Has its own inode? | no, shares one | yes |
| Survives deleting the original | **yes** | no — dangles |
| Can cross filesystems | no | yes |
| Can point at a directory | no (not normally) | yes |
| `ls -l` shows | `-rw-r--r--` | `lrwxrwxrwx ... -> target` |
| Size | size of the data | length of the target path |

### Interview answer

*What is the difference between a soft link and a hard link?*

A hard link is another directory entry for the same inode, so it is indistinguishable from
the original and keeps the data alive as long as it exists — the inode is freed only when
its link count reaches zero. A soft link is a small separate file whose content is a path,
resolved at access time, so it breaks if the target is moved or deleted — but it can cross
filesystems and can point at a directory, which a hard link cannot.

---

## Task 2: `useradd` vs `adduser`

### What the task asked

Compare the two ways of creating a user.

### Commands

```bash
useradd tu-useradd
adduser --disabled-password --gecos '' tu-adduser
```

`adduser` normally prompts for a password and full name. The two flags make it
non-interactive so the run is reproducible; they do not change what it sets up.

### Output

![useradd vs adduser](screenshots/task2-adduser-vs-useradd.png)

`useradd` printed **nothing whatsoever** and exited 0. `adduser` narrated every step:

```text
$ useradd tu-useradd; echo "exit=$?  (no output above means it printed nothing)"
exit=0  (no output above means it printed nothing)

$ adduser --disabled-password --gecos '' tu-adduser
info: Adding user `tu-adduser' ...
info: Selecting UID/GID from range 1000 to 59999 ...
info: Adding new group `tu-adduser' (1002) ...
info: Adding new user `tu-adduser' (1002) with group `tu-adduser (1002)' ...
info: Creating home directory `/home/tu-adduser' ...
info: Copying files from `/etc/skel' ...
info: Adding new user `tu-adduser' to supplemental / extra groups `users' ...
info: Adding user `tu-adduser' to group `users' ...
```

The difference shows up in what actually landed on the box:

```text
$ grep -E '^tu-' /etc/passwd
tu-useradd:x:1001:1001::/home/tu-useradd:/bin/sh
tu-adduser:x:1002:1002:,,,:/home/tu-adduser:/bin/bash

$ ls -ld /home/tu-useradd /home/tu-adduser
ls: cannot access '/home/tu-useradd': No such file or directory
drwxr-x--- 2 tu-adduser tu-adduser 4096 Sep  4 19:57 /home/tu-adduser

$ ls -A /home/tu-adduser
.bash_logout
.bashrc
.profile
```

This is the bit worth noticing: `useradd` wrote `/home/tu-useradd` into `/etc/passwd` **but
never created that directory**. The account exists and is broken — log in as it and you
land in a home that is not there. It also left the shell as `/bin/sh`. `adduser` created
the home, populated it from `/etc/skel` (hence the three dotfiles), and set `/bin/bash`.

| | `useradd` | `adduser` |
|---|---|---|
| What it is | low-level binary | Perl wrapper **around** `useradd` |
| Home directory | not created (unless `-m`) | created |
| `/etc/skel` copied in | no | yes |
| Default shell | `/bin/sh` | `/bin/bash` |
| Password | not set, not prompted | prompts (interactive) |
| Output | silent | explains each step |
| Available on | every Linux | Debian/Ubuntu family |

**Which to use:** `adduser` when you are sitting at a Debian/Ubuntu box creating a real
account. `useradd` in scripts and on distros that have no `adduser` — remembering to pass
`-m -s /bin/bash` yourself, or you get the half-made account above.

### Cleanup

```bash
userdel -r tu-useradd
userdel -r tu-adduser
```

---

## What I learned

- `ls -li` is the fastest way to tell a hard link from a copy: same inode, link count above 1.
- A symlink's *size* being the length of its target path is a neat tell that it stores text,
  not a pointer to data.
- `rm` decrements a link count rather than destroying data. That reframes what "deleting a
  file" means — you are removing a name, and the data goes when the last name does.
- `useradd` silently producing a broken account is a good example of a low-level tool doing
  exactly what it was told and not one thing more. `adduser` is the policy layer on top.

## Problems I hit

- **`adduser: command not found`.** The `ubuntu:24.04` image is minimal and ships `useradd`
  (from `passwd`) but not `adduser`. `apt-get install -y adduser` fixed it. Slightly funny
  that the task's whole point — the two commands differ — showed up first as one of them
  not existing.
- **The host machine could not run this task at all.** macOS manages users through `dscl`,
  not `useradd`/`adduser`, and `stat -c` is GNU syntax that the BSD `stat` on macOS rejects.
  Translating every command into a BSD equivalent would have demonstrated macOS rather than
  Linux, so I moved the whole task into a container instead. The useful takeaway is which of
  these commands are *Linux* specifically and which are *Unix* generally — `ln`, `ls -l` and
  `rm` are portable; `stat -c`, `useradd` and `/etc/skel` are not.
