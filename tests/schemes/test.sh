#!/bin/bash

bindir=$(dirname "$0")
cd "$bindir"

damon_debugfs="/sys/kernel/debug/damon"
damo="../../damo"

test_stat() {
	python ./stairs.py &
	stairs_pid=$!
	sudo "$damo" schemes -c ./stat_cold_memory.damos "$stairs_pid" &

	total_applied=0
	while ps --pid "$stairs_pid" > /dev/null
	do
		applied=$(sudo cat "$damon_debugfs"/schemes | awk '{print $NF}')
		sleep 2
	done

	if [ "$applied" -eq 0 ]
	then
		echo "FAIL schemes-stat"
		exit 1
	fi
	echo "PASS schemes-stat ($applied cold memory found)"
}

if ! sudo "$damo" features supported | grep schemes
then
	echo "SKIP $(basename $(pwd))"
	exit 0
fi

echo "PASS $(basename $(pwd))"
