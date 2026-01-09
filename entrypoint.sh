#!/bin/sh

CRASH_COUNT=0

cd /privacy-manager/

while true;
do
  echo "Starting Privacy Manager"

  python3 ./main.py

  if [ $? -ne 0 ]; then
    CRASH_COUNT=$((CRASH_COUNT + 1))
    echo "Privacy Manager crashed ${CRASH_COUNT} times, restarting..."
  else
    echo "Privacy Manager exited normally"
    break
  fi
done
