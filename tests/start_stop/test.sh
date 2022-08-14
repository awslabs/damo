#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

bindir=$(dirname "$0")
cd "$bindir"

damo="../../damo"

testname=$(basename $(pwd))

damon_interfaces=""
if [ -d "/sys/kernel/debug/damon" ]
then
	damon_interfaces+="debugfs "
fi

if [ -d "/sys/kernel/mm/damon" ]
then
	damon_interfaces+="sysfs "
fi

if [ "$damon_interfaces" = "" ]
then
	echo "SKIP $(basename $(pwd)) (DAMON interface not found)"
	exit 0
fi

for damon_interface in $damon_interfaces
do
	testname2="$testname $damon_interface"
	sudo "$damo" start paddr
	if ! pidof kdamond.0 > /dev/null
	then
		echo "FAIL $testname2 (kdamond.0 pid not found after start)"
		exit 1
	fi

	sudo timeout 3 "$damo" record ongoing &> /dev/null
	if ! "$damo" validate
	then
		echo "FAIL $testname2 (invalid record file)"
		exit 1
	fi

	sudo "$damo" stop
	if pidof kdamond.0 > /dev/null
	then
		echo "FAIL $testname2 (kdamond.0 pid found after stop)"
		exit 1
	fi
done

echo "PASS $(basename $(pwd))"
