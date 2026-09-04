"""Run a spec of shell commands (Windows or WSL), capture real output, emit
term-jobs JSON for shoot-term.mjs."""
import json, os, subprocess, sys

BASH = r"C:\Program Files\Git\bin\bash.exe"
WSL = r"C:\Windows\System32\wsl.exe"
# Extra PATH entries for the shell the commands run in. Adjust to your machine.
WINPATH = os.environ.get(
    "CAPTURE_PATH",
    "/usr/bin:/c/Windows/System32:/c/Program Files/Docker/Docker/resources/bin:/c/Program Files/Git/cmd",
)


def run_win(cmd, cwd=None):
    full = f'export PATH="{WINPATH}"; export MSYS_NO_PATHCONV=1; {cmd}'
    p = subprocess.run([BASH, "-c", full], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True, cwd=cwd, errors="replace")
    return p.stdout or ""


WSL_USER = os.environ.get("WSL_USER", "")  # empty = WSL default user


def run_wsl(cmd, user=None, cwd=None):
    user = user or WSL_USER
    pre = f"export TERM=dumb LINES=50 COLUMNS=118; "
    if cwd:
        pre += f"cd {cwd} 2>/dev/null; "
    args = [WSL, "-d", "Ubuntu"]
    if user == "root":
        args += ["-u", "root"]
    args += ["bash", "-s"]
    p = subprocess.run(args, input=(pre + cmd).encode("utf-8"), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
    return p.stdout.decode("utf-8", errors="replace").replace(chr(13), "")


def execute(job, cmd):
    if job.get("shell") == "wsl":
        return run_wsl(cmd, job.get("wsl_user"), job.get("cwd"))
    return run_win(cmd, job.get("cwd"))


def main(spec_path, out_path):
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)

    jobs = []
    for job in spec:
        if job.get("setup"):
            print(f"  [setup] {job['title']}", flush=True)
            execute(job, job["setup"])
        lines = []
        for c in job["cmds"]:
            out = execute(job, c)
            lines.append({"cmd": c, "out": out})
            print(f"    captured: {c[:66]}", flush=True)
        jobs.append({"title": job["title"], "out": job["out"], "lines": lines})

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=1)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
