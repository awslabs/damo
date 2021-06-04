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

test_wmarks() {
	if ! sudo "$damo" features supported | grep schemes_wmarks > /dev/null
	then
		echo "SKIP schemes-wmarks (unsupported)"
		return
	fi

	mem_total=$(grep MemTotal /proc/meminfo | awk '{print $2}')
	mem_free=$(grep MemFree /proc/meminfo | awk '{print $2}')
	mem_free_rate=$((mem_free * 1000 / mem_total))
	echo "$mem_total $mem_free $mem_free_rate"
	if [ "$mem_free_rate" -gt 970 ] || [ "$mem_free_rate" -lt 100 ]
	then
		echo "SKIP schemes-wmarks (memory pressure $mem_free_rate)"
		return
	fi

	scheme="4K max  min min  1s max  stat"
	scheme+="  5G 1s 0 3 7"
	scheme+="  free_mem_rate 1s"

	echo "$scheme 50 40 30" > test_wmarks.damos
	sudo timeout 5 "$damo" schemes -c ./test_wmarks.damos paddr &
	damo_pid=$!

	before=$(sudo cat "$damon_debugfs"/schemes | awk '{print $NF}')
	sleep 3
	after=$(sudo cat "$damon_debugfs"/schemes | awk '{print $NF}')
	while ps --pid "$damo_pid" > /dev/null
	do
		sleep 1
	done

	applied=$((after - before))
	if [ "$applied" -ne 0 ]
	then
		echo "FAIL schemes-wmarks (high watermark doesn't works)"
		exit 1
	fi

	echo "$scheme 999 980 100" > test_wmarks.damos
	sudo timeout 5 "$damo" schemes -c ./test_wmarks.damos paddr &
	damo_pid=$!

	before=$(sudo cat "$damon_debugfs"/schemes | awk '{print $NF}')
	sleep 3
	after=$(sudo cat "$damon_debugfs"/schemes | awk '{print $NF}')
	while ps --pid "$damo_pid" > /dev/null
	do
		sleep 1
	done

	applied=$((after - before))
	if [ "$applied" -le 0 ]
	then
		echo "FAIL schemes-wmarks (mid watermark doesn't works)"
		exit 1
	fi

	echo "$scheme 999 990 980" > test_wmarks.damos
	sudo timeout 5 "$damo" schemes -c ./test_wmarks.damos paddr &
	damo_pid=$!

	before=$(sudo cat "$damon_debugfs"/schemes | awk '{print $NF}')
	sleep 3
	after=$(sudo cat "$damon_debugfs"/schemes | awk '{print $NF}')
	while ps --pid "$damo_pid" > /dev/null
	do
		sleep 1
	done

	applied=$((after - before))
	if [ "$applied" -ne 0 ]
	then
		echo "FAIL schemes-wmarks (low watermark doesn't works)"
		exit 1
	fi

	echo "PASS schemes-wmarks"
}

if ! sudo "$damo" features supported | grep -w "schemes" > /dev/null
then
	echo "SKIP $(basename $(pwd))"
	exit 0
fi

test_stat
test_wmarks

echo "PASS $(basename $(pwd))"
