#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

bindir=$(dirname "$0")
cd "$bindir"

damo="../../damo"

test_features_list()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 <damon interface>"
		exit 1
	fi
	local testname="features-list $damon_interface"

	damon_interface=$1
	expected="expected_features_list_$damon_interface"
	result="result_features_list"
	sudo "$damo" features --damon_interface "$damon_interface" 2> /dev/null \
		| awk -F':' '{print $1}' > "$result"
	if ! diff -q "$expected" "$result"
	then
		echo "FAIL $testname"
		exit 1
	fi
	sudo rm -f "$result"
	echo "PASS $testname"

}

test_features_list "debugfs"
test_features_list "sysfs"

echo "PASS $(basename $(pwd))"
