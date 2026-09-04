"""Run a spec of shell commands, capture real output, emit term-jobs JSON for
shoot-term.mjs.

Backends (job field "shell"):
  "local"  - a bash on this machine. Default on macOS/Linux.
  "docker" - bash inside a running container, named by the job's "container".
  "wsl"    - WSL Ubuntu on Windows.
  "win"    - Git Bash on Windows. Default on Windows.
"""
import json, os, platform, subprocess, sys

BASH = r"C:\Program Files\Git\bin\bash.exe"
WSL = r"C:\Windows\System32\wsl.exe"
# Extra PATH entries for the shell the commands run in. Adjust to your machine.
WINPATH = os.environ.get(
    "CAPTURE_PATH",
    "/usr/bin:/c/Windows/System32:/c/Program Files/Docker/Docker/resources/bin:/c/Program Files/Git/cmd",
)
IS_WINDOWS = platform.system() == "Windows"


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


# Same environment for every backend so a capture does not depend on the operator's
# shell: no colour escapes, no pager stealing the output, a fixed width to wrap at.
PRE = "export TERM=dumb LINES=50 COLUMNS=118 PAGER=cat GIT_PAGER=cat CLICOLOR=0; "


def run_local(cmd, cwd=None):
    """bash on this machine (macOS/Linux)."""
    pre = PRE
    if cwd:
        pre += f'cd "{os.path.expandvars(cwd)}" 2>/dev/null; '
    p = subprocess.run(["bash", "-s"], input=(pre + cmd).encode("utf-8"),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.stdout.decode("utf-8", errors="replace").replace(chr(13), "")


def run_docker(cmd, container, user=None, cwd=None):
    """bash inside a running container - how Linux-only commands get run from macOS."""
    pre = PRE
    if cwd:
        pre += f"cd {cwd} 2>/dev/null; "
    args = ["docker", "exec", "-i"]
    if user:
        args += ["-u", user]
    args += [container, "bash", "-s"]
    p = subprocess.run(args, input=(pre + cmd).encode("utf-8"),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.stdout.decode("utf-8", errors="replace").replace(chr(13), "")


def execute(job, cmd):
    shell = job.get("shell") or ("win" if IS_WINDOWS else "local")
    if shell == "wsl":
        return run_wsl(cmd, job.get("wsl_user"), job.get("cwd"))
    if shell == "docker":
        container = job.get("container")
        if not container:
            sys.exit(f'job "{job["title"]}" uses shell "docker" but has no "container"')
        return run_docker(cmd, container, job.get("user"), job.get("cwd"))
    if shell == "local":
        return run_local(cmd, job.get("cwd"))
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
