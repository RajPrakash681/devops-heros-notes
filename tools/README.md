# Screenshot tooling (optional)

Two small [Playwright](https://playwright.dev/) scripts for capturing proof of your work.
Both take **real output from your own machine** — they do not invent anything. Ordinary
screenshots are perfectly fine; this just makes them consistent and easy to regenerate
after you change something.

## Install

```bash
cd tools
npm install
npx playwright install chromium
```

Needs Node 18+ and Python 3.9+.

## 1. Browser screenshots — `shoot-web.mjs`

Screenshots a URL your container is actually serving, inside a frame showing the real URL.
It sends a request first and **fails loudly if the URL does not return 200**, so a
screenshot only exists if something really answered.

```bash
cat > web.json <<'EOF'
[
  {"url": "http://localhost:3001", "out": "../session6-7-docker/task/screenshots/nodejs-app.png", "height": 185}
]
EOF

node shoot-web.mjs web.json
```

- `url` — must be live when you run it
- `out` — where the PNG goes
- `height` — page area height in px; shrink it to crop off empty space

## 2. Terminal screenshots — `capture.py` + `shoot-term.mjs`

`capture.py` runs commands and records their genuine stdout/stderr to JSON.
`shoot-term.mjs` renders that JSON as a terminal-styled PNG.

```bash
cat > spec.json <<'EOF'
[
  {
    "title": "Session 2 Task 1 - hard links vs soft links",
    "out": "../session2-linux/task/screenshots/task1-links.png",
    "shell": "wsl",
    "cwd": "$HOME/session2-linux-task",
    "setup": "rm -rf $HOME/session2-linux-task && mkdir -p $HOME/session2-linux-task && cd $HOME/session2-linux-task && echo hello > file1.txt && ln file1.txt hardlink.txt && ln -s file1.txt softlink.txt",
    "cmds": ["ls -li", "stat -c '%n inode=%i links=%h' file1.txt hardlink.txt softlink.txt"]
  }
]
EOF

python capture.py spec.json jobs.json
node shoot-term.mjs jobs.json
```

Per job:

| Field | Meaning |
|---|---|
| `title` | Shown in the window title bar |
| `out` | Where the PNG goes |
| `shell` | `"wsl"` to run in WSL, omit to run in Git Bash on Windows |
| `wsl_user` | `"root"` for commands needing root (WSL gives root with no password) |
| `cwd` | Working directory |
| `setup` | Runs first, output discarded — use it for scaffolding you do not want pictured |
| `cmds` | One entry per command; each is captured and displayed with its output |

Environment overrides: `CAPTURE_PATH` to change the PATH commands run with, `WSL_USER` to
change the default WSL user.

## Notes

- Each command runs in its own shell, so state that lives in the shell (variables, `cd`)
  does not persist between them. State on disk does — which is why `cwd` is per job.
- `capture.py` passes stdin as **bytes** on purpose. With text mode, Windows turns `\n`
  into `\r\n`, and a stray CR ends up inside piped input — which will silently corrupt
  filenames your commands create.
- Merge stderr into the command yourself if ordering matters; the capture already combines
  the two streams so interleaving is preserved.
- Re-run a capture after changing anything, so the screenshot and your write-up never drift
  apart. If you quote output in the README, make sure it is the same run as the picture.
