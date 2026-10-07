# Setup

Everything the DevOps Heros homework needs: the course material for each session, plus a
write-up template for every task.

## 1. Get the repo

```bash
git clone https://github.com/RajPrakash681/devops-heros-notes.git
cd devops-heros-notes
```

## 2. Fill in the write-ups

Each `task/README.md` starts with:

```markdown
- **Name:** Raj Prakash
- **Enrollment No:** _(your enrollment number)_
```

Fill the enrollment number in as you do each task. Do not leave the placeholder in a
submission.

## 3. Working through a session

1. Read the session notes in the `sessionN-*/` folder.
2. Find the task in the homework doc (linked from the root [README](README.md)).
3. Actually run it — on WSL/Linux for the Linux, shell and networking sessions; with Docker
   for sessions 6–8; with minikube or kind for sessions 9–10.
4. Write up what you ran and what came back in `task/README.md`, and put your screenshots
   in `task/screenshots/`.
5. Commit as you go, one session at a time, rather than in a single big commit at the end.

## 4. What you need installed

| Sessions | Needs |
|---|---|
| 2, 3, 4, 5 | A Linux shell. On Windows: `wsl --install -d Ubuntu`. |
| 6–7, 8 | Docker (Docker Desktop on Windows/macOS, or Docker Engine on Linux). |
| 9, 10 | A local Kubernetes cluster: `minikube start --driver=docker`, or `kind`. |
| 11–15 | The kind cluster in [`session-11-kubernetes-services/task/kind-cluster.yaml`](session-11-kubernetes-services/task/kind-cluster.yaml) plus [`cluster-setup.sh`](session-11-kubernetes-services/task/cluster-setup.sh) (metrics-server, MetalLB, ingress-nginx); Helm 3 for session 15. |
| 16, 17, 21 | Nothing local — the pipelines run on GitHub Actions from [`.github/workflows/`](.github/workflows/). |
| 18, 19 | Terraform ≥ 1.6. Without AWS credentials, a local AWS API emulator (moto in Docker) — see each task README. |
| 20 | Docker Compose (Prometheus, Grafana) and the kind cluster (Argo CD). |

Some sessions need tools that are not installed by default. On Ubuntu, session 4 needs:

```bash
sudo apt-get install dnsutils iputils-tracepath
```

## A few things that will save you time

- **Line endings.** The included `.gitattributes` forces LF. Without it, git on Windows
  commits CRLF and a shell script checked out on Linux fails with
  `bad interpreter: /usr/bin/env bash^M`.
- **Paste the real text output**, not only a screenshot. It is searchable, it survives a
  broken image, and it is much easier to check against.
- **Write down the errors you hit** and how you fixed them. That section of the template is
  the most useful part of the whole write-up when you come back to it.
- **Your screenshots should come from your own machine.** Hostnames, IPs, container IDs and
  timestamps are all visible in terminal output, so borrowed screenshots are obvious — and
  the point of the exercise is the run, not the picture.
