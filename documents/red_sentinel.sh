#!/bin/zsh
# Independent RED stop: a separate process runs the gate in a loop and SIGKILLs the target PID the moment it reads RED.
# usage: red_sentinel.sh <pid> <logfile> [gate command, default: python3 documents/gate0.py]
PID=$1; LOG=$2; GATE=${3:-"python3 ${0:A:h}/gate0.py"}
while kill -0 $PID 2>/dev/null; do
  G=$(eval "$GATE" 2>&1 | tail -1)
  echo "$(date +%H:%M:%S) $G" >> $LOG
  if [[ "$G" == gate=RED* ]]; then
    kill -9 $PID; echo "$(date +%H:%M:%S) RED_SENTINEL_KILL pid=$PID" >> $LOG; exit 9
  fi
  sleep 1
done
