#!/usr/bin/env bash
# Sample a rollout in namespace s10.
# Usage: ./watch-rollout.sh <app-label> <service> <samples> [interval-seconds]
# Each line: wall-clock time | pods grouped as "count x version READY STATUS" |
# what one request through the Service returned (from the "client" pod).
app=$1 svc=$2 n=${3:-20} dt=${4:-1}
for i in $(seq 1 "$n"); do
  pods=$(kubectl -n s10 get pods -l app="$app" -L version --no-headers 2>/dev/null |
    awk '{print $NF, $2, $3}' | sort | uniq -c | awk '{printf "%sx %s %s %s | ", $1, $2, $3, $4}')
  resp=$(kubectl -n s10 exec client -- curl -sS -m 1 "http://$svc" 2>&1 |
    grep -oE 'VERSION: v[0-9]|Failed to connect|timed out|Could not resolve' | head -1)
  printf '%s  %-58s -> %s\n' "$(date +%T)" "${pods:-(no pods)}" "${resp:-NO RESPONSE}"
  sleep "$dt"
done
