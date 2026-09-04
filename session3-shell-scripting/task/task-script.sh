#!/usr/bin/env bash
#
# Session 3 - Shell Scripting task.
#
# Covers everything task.md asks for:
#   - prints the current date
#   - prints the hostname and the username
#   - writes process information into a file called process.log
#   - prints a name, roll number and comment
#   - uses variables, takes input, and creates a file and a directory
#
# Usage:  bash task-script.sh
#         (or pipe the five answers in:  printf 'a\nb\nc\nd\ne\n' | bash task-script.sh)

set -u

# ---------- variables (command substitution) ----------
current_date=$(date)
host_name=$(hostname)
user_name=$(whoami)
kernel=$(uname -sr)
uptime_line=$(uptime | sed 's/^ *//')

echo "===== System information ====="
echo "Date     : $current_date"
echo "Hostname : $host_name"
echo "User     : $user_name"
echo "Kernel   : $kernel"
echo "Uptime   : $uptime_line"
echo

# ---------- take input ----------
read -rp "Enter your name: " name
read -rp "Enter your roll number: " roll_no
read -rp "Enter a comment: " comment
read -rp "Enter a directory name to create: " dir_name
read -rp "Enter a file name for the process log: " file_name
echo

# ---------- create a directory and a file inside it ----------
mkdir -p "$dir_name"
ps -ef > "$dir_name/$file_name"

proc_count=$(( $(wc -l < "$dir_name/$file_name") - 1 ))   # -1 drops the ps header row

echo "===== Files created ====="
echo "Directory : $dir_name/"
echo "File      : $dir_name/$file_name  ($proc_count processes recorded)"
echo
echo "First few lines of $dir_name/$file_name:"
head -5 "$dir_name/$file_name"
echo

# ---------- print what was entered ----------
echo "===== Details entered ====="
echo "My name is $name"
echo "My roll number is $roll_no"
echo "My comment is: $comment"
