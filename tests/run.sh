#!/bin/bash

bindir=$(dirname "$0")
cd "$bindir"

for testfile in */test.sh
do
	"$testfile"
	if [ "$?" -ne 0 ]
	then
		exit 1
	fi
done

echo "PASS ALL"
