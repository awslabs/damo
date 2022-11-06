#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

bindir=$(dirname "$0")
damo_dir="$bindir/../../"

for test_file in "$damo_dir"/test_*.py
do
	for py in "python" "python3"
	do
		if "$py" "$test_file" &> /dev/null
		then
			echo "PASS unittest-$py $(basename $test_file)"
		else
			echo "FAIL unittest-$py $(basename $test_file)"
			exit 1
		fi
	done
done
