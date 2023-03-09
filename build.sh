#!/usr/bin/env bash

# directs output into a build folder for us, this gets the output from the compile file. 
mkdir -p ./build/
# clean
rm -f ./build/*.teal

set -e # die on error

python ./compile.py "$1" ./build/approval.teal ./build/clear.teal