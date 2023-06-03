#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

bindir=$(dirname "$0")

for test_file in "$bindir"/test_*.py
do
	for py in "python3"
	do
		if "$py" "$test_file" &> /dev/null
		then
			echo "PASS unit-$py $(basename $test_file)"
		else
			echo "FAIL unit-$py $(basename $test_file)"
			exit 1
		fi
	done
done
