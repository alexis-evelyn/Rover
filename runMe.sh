#!/bin/bash

if [ -f "./venv/bin/activate" ]
then
    echo "Using Venv ./venv/"
    source ./venv/bin/activate
fi

# TODO: Figure Out How To Display STDOUT To Terminal And Record Both STDOUT and STDERR To One File
# { python3 main.py "$@" | tee /dev/stdout ; } 2>&1 | tee -a ./working/tweet-download.log

if [ ! -d "./working" ]; then
  echo "Making Working Directory"
  mkdir ./working
fi

python3 src/main.py "$@" 2>&1 | tee ./working/tweet-download.log