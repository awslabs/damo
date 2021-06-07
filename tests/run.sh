#!/bin/bash

bindir=$(dirname "$0")
cd "$bindir"

for test_dir in report schemes damon_reclaim
do
	testfile="./$test_dir/test.sh"
	"$testfile"
	if [ "$?" -ne 0 ]
	then
		exit 1
	fi
done

echo "PASS ALL"
