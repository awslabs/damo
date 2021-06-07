#!/bin/bash

bindir=$(dirname "$0")
cd "$bindir"

damon_debugfs="/sys/kernel/debug/damon"
damo="../../damo"

test_stat() {
	python ./stairs.py &
	stairs_pid=$!
	sudo "$damo" schemes -c ./stat_cold_memory.damos "$stairs_pid" > \
		/dev/null &

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

ensure_free_mem_ratio() {
	upperbound=$1
	lowerbound=$2

	mem_total=$(grep MemTotal /proc/meminfo | awk '{print $2}')
	mem_free=$(grep MemFree /proc/meminfo | awk '{print $2}')
	mem_free_rate=$((mem_free * 1000 / mem_total))

	# Ensure free memory ratio is between 99% and 10%
	if [ "$mem_free_rate" -gt "$upperbound" ] || \
		[ "$mem_free_rate" -lt "$lowerbound" ]
	then
		echo "SKIP schemes-wmarks ($mem_free_rate free mem rate)"
		exit
	fi
}

measure_scheme_applied() {
	scheme=$1
	target=$2
	wait_for=$3

	echo "$scheme" > test_scheme.damos

	timeout_after=$((wait_for + 2))
	sudo timeout "$timeout_after" \
		"$damo" schemes -c test_scheme.damos "$target" > /dev/null &
	damo_pid=$!

	sudo cat "$damon_debugfs/schemes"
	before=$(sudo cat "$damon_debugfs/schemes" | awk '{print $NF}')
	if [ "$before" = "" ]
	then
		before=0
	fi
	sleep "$wait_for"
	after=$(sudo cat "$damon_debugfs/schemes" | awk '{print $NF}')

	while ps --pid "$damo_pid" > /dev/null
	do
		sleep 1
	done

	applied=$((after - before))
}

test_wmarks() {
	if ! sudo "$damo" features supported | grep -w schemes_wmarks > \
		/dev/null
	then
		echo "SKIP schemes-wmarks (unsupported)"
		return
	fi

	scheme_prefix="4K max  min min  1s max  stat"
	scheme_prefix+="  5G 1s 0 3 7"
	scheme_prefix+="  free_mem_rate 1s"

	# Test high watermark-based deactivation
	ensure_free_mem_ratio 990 100
	applied=42
	measure_scheme_applied "$scheme_prefix 50 40 30" "paddr" 3
	if [ "$applied" -ne 0 ]
	then
		echo "FAIL schemes-wmarks (high watermark doesn't works)"
		exit 1
	fi

	# Test mid-low watermarks-based activation
	ensure_free_mem_ratio 990 100
	applied=0
	measure_scheme_applied "$scheme_prefix 999 995 100" "paddr" 3
	if [ "$applied" -le 0 ]
	then
		echo "FAIL schemes-wmarks (mid watermark doesn't works)"
		exit 1
	fi

	# Test low watermark-based deactivation
	ensure_free_mem_ratio 990 100
	applied=42
	measure_scheme_applied "$scheme_prefix 999 998 995" "paddr" 3
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
