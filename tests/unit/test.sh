#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

bindir=$(dirname "$0")

for test_file in "$bindir"/test_*.py
do
	if python3 "$test_file" &> /dev/null
	then
		echo "PASS unit $(basename $test_file)"
	else
		echo "FAIL unit $(basename $test_file)"
		exit 1
	fi
done
