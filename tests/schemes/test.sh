#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

bindir=$(dirname "$0")
cd "$bindir"

damon_debugfs="/sys/kernel/debug/damon"
damo="../../damo"

__test_stat() {
	if [ $# -ne 3 ]
	then
		echo "Usage: $0 <speed limit> <use scheme file> <damon interface>"
		exit 1
	fi

	local speed_limit=$1
	local use_scheme_file=$2
	local damon_interface=$3

	scheme="4K max    min min    1s max    stat"
	if [ ! "$speed_limit" = "" ]
	then
		speed_limit+="B"
		scheme+=" $speed_limit 1s"
	fi

	if [ "$use_scheme_file" = "use_scheme_file" ]
	then
		echo "$scheme" > test_scheme.damos
		scheme="./test_scheme.damos"
	fi

	python ./stairs.py &
	stairs_pid=$!
	sudo "$damo" schemes -c "$scheme" "$stairs_pid" \
		--damon_interface "$damon_interface" > /dev/null &

	start_time=$SECONDS
	applied=0
	while ps --pid "$stairs_pid" > /dev/null
	do
		applied=$(__measure_scheme_applied "$damon_interface")
		sleep 1
	done
	measure_time=$((SECONDS - start_time))

	if [ "$use_scheme_file" = "use_scheme_file" ]
	then
		rm "$scheme"
	fi
}

test_stat() {
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 <damon interface>"
		exit 1
	fi
	local damon_interface=$1

	testname="schmes-stat $damon_interface"

	__test_stat 0 "dont_use_scheme_file" "$damon_interface"
	if [ "$applied" -eq 0 ]
	then
		echo "FAIL $testname"
		exit 1
	fi
	echo "PASS $testname ($applied cold memory found)"

	testname="schemes-stat-using-scheme-file $damon_interface"
	__test_stat 0 "use_scheme_file" "$damon_interface"
	if [ "$applied" -eq 0 ]
	then
		echo "FAIL $testname"
		exit 1
	fi
	echo "PASS $testname ($applied cold memory found)"

	testname="schemes-speed-limit $damon_interface"
	if ! sudo "$damo" features supported \
		--damon_interface "$damon_interface" | grep -w schemes_speed_limit > \
		/dev/null
	then
		echo "SKIP $testname (unsupported)"
		return
	fi

	speed=$((applied / measure_time))
	if [ "$speed" -lt $((4 * 1024 * 100)) ]
	then
		echo "SKIP $testname (too slow detection: $speed)"
		return
	fi
	speed_limit=$((speed / 2))

	__test_stat $speed_limit "dont_use_scheme_file" "$damon_interface"
	speed=$((applied / measure_time))
	if [ "$speed" -gt $((speed_limit * 11 / 10)) ]
	then
		echo "FAIL $testname ($speed > $speed_limit)"
		exit 1
	fi
	echo "PASS $testname ($speed < $speed_limit)"
}

ensure_free_mem_ratio() {
	upperbound=$1
	lowerbound=$2

	mem_total=$(grep MemTotal /proc/meminfo | awk '{print $2}')
	mem_free=$(grep MemFree /proc/meminfo | awk '{print $2}')
	mem_free_rate=$((mem_free * 1000 / mem_total))

	if [ "$mem_free_rate" -gt "$upperbound" ] || \
		[ "$mem_free_rate" -lt "$lowerbound" ]
	then
		echo "SKIP schemes-wmarks ($mem_free_rate free mem rate)"
		exit
	fi
}

__measure_scheme_applied() {
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 <damon_interface>"
		exit 1
	fi
	local damon_interface=$1
	if [ "$damon_interface" = "debugfs" ]
	then
		sudo cat "$damon_debugfs/schemes" | \
			awk '{if (NF==23) print $20; else print $NF;}'
	elif [ "$damon_interface" = "sysfs" ]
	then
		while [ "$(cat /sys/kernel/mm/damon/admin/kdamonds/0/state)" = "off" ]
		do
			sleep 0.1
		done
		echo update_schemes_stats > "/sys/kernel/mm/damon/admin/kdamonds/0/state"
		sudo cat "/sys/kernel/mm/damon/admin/kdamonds/0/contexts/0/schemes/0/stats/sz_tried"
	else
		echo "wrong damon_interface ($damon_interface)"
		exit 1
	fi
}

measure_scheme_applied() {
	if [ $# -ne 4 ]
	then
		echo" Usage: $0 <scheme> <target> <wait_for> <damon_interface>"
		exit 1
	fi
	scheme=$1
	target=$2
	wait_for=$3
	local damon_interface=$4

	timeout_after=$((wait_for + 2))
	sudo timeout "$timeout_after" \
		"$damo" schemes -c "$scheme" \
		--damon_interface "$damon_interface" "$target" > /dev/null &
	damo_pid=$!

	before=$(__measure_scheme_applied "$damon_interface")
	if [ "$before" = "" ]
	then
		before=0
	fi
	sleep "$wait_for"
	after=$(__measure_scheme_applied "$damon_interface")

	wait "$damo_pid"

	applied=$((after - before))
}

test_wmarks() {
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 <damon interface>"
		exit 1
	fi
	local damon_interface=$1
	testname="schemes-wmarks $damon_interface"

	if ! sudo "$damo" features supported \
		--damon_interface "$damon_interface" | \
		grep -w schemes_wmarks > /dev/null
	then
		echo "SKIP $testname (unsupported)"
		return
	fi
	if ! sudo "$damo" features supported \
		--damon_interface "$damon_interface" | \
		grep -w paddr > /dev/null
	then
		echo "SKIP $testname (paddr unsupported)"
		return
	fi

	scheme_prefix="4K max  min min  1s max  stat"
	scheme_prefix+="  5G 1s 0 3 7"
	scheme_prefix+="  free_mem_rate 1s"

	# Test high watermark-based deactivation
	ensure_free_mem_ratio 990 100
	applied=42
	measure_scheme_applied "$scheme_prefix 50 40 30" "paddr" 3 \
		"$damon_interface"
	if [ "$applied" -ne 0 ]
	then
		echo "FAIL $testname (high watermark doesn't works)"
		exit 1
	fi

	# Test mid-low watermarks-based activation
	ensure_free_mem_ratio 990 100
	applied=0
	measure_scheme_applied "$scheme_prefix 999 995 100" "paddr" 3 \
		"$damon_interface"
	if [ "$applied" -le 0 ]
	then
		echo "FAIL $testname (mid watermark doesn't works)"
		exit 1
	fi

	# Test low watermark-based deactivation
	ensure_free_mem_ratio 990 100
	applied=42
	measure_scheme_applied "$scheme_prefix 999 998 995" "paddr" 3 \
		"$damon_interface"
	if [ "$applied" -ne 0 ]
	then
		echo "FAIL $testname (low watermark doesn't works)"
		exit 1
	fi

	echo "PASS $testname"
}

for damon_interface in "debugfs" "sysfs"
do
	if ! sudo "$damo" features supported \
	       --damon_interface "$damon_interface" | \
	       grep -w "schemes" > /dev/null
	then
		echo "SKIP $(basename $(pwd))"
		exit 0
	fi

	test_stat "$damon_interface"
	test_wmarks "$damon_interface"
done

echo "PASS $(basename $(pwd))"
