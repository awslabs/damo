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

	scheme=$(cat cold_mem_stat_damos_template.json)
	if [ ! "$speed_limit" = "" ]
	then
		speed_limit+=" B"
		scheme=$(echo "$scheme" | \
			sed "s/quotas_sz_bytes_to_be_replaced/$speed_limit/" \
			| sed 's/quotas_reset_interval_ms_to_be_replaced/1 s/')
	else
		scheme=$(echo "$scheme" | \
			sed "s/quotas_sz_bytes_to_be_replaced/0 B/" \
			| sed 's/quotas_reset_interval_ms_to_be_replaced/max/')
	fi

	if [ "$use_scheme_file" = "use_scheme_file" ]
	then
		echo "$scheme" > test_scheme.json
		scheme="./test_scheme.json"
	fi

	python ./stairs.py &
	stairs_pid=$!
	sudo "$damo" schemes -c "$scheme" "$stairs_pid" \
		--damon_interface "$damon_interface" &> /dev/null &

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

	testname="schemes-stat $damon_interface"

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
		--damon_interface "$damon_interface" 2> /dev/null | \
		grep -w schemes_speed_limit > /dev/null
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
		return 1
	fi
	return 0
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
		i=0
		while [ "$(cat /sys/kernel/mm/damon/admin/kdamonds/0/state)" = "off" ]
		do
			i=$((i + 1))
			if [ $i -gt 50 ]
			then
				>&2 echo "Seems kdamond already finished"
				exit
			fi
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
		--damon_interface "$damon_interface" "$target" &> /dev/null &
	damo_pid=$!

	while true
	do
		# wait kdamond
		if ! pgrep kdamond.0 > /dev/null
		then
			sleep 0.1
		else
			break
		fi
	done

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
		--damon_interface "$damon_interface" 2> /dev/null | \
		grep -w schemes_wmarks > /dev/null
	then
		echo "SKIP $testname (unsupported)"
		return
	fi
	if ! sudo "$damo" features supported \
		--damon_interface "$damon_interface" 2> /dev/null | \
		grep -w paddr > /dev/null
	then
		echo "SKIP $testname (paddr unsupported)"
		return
	fi

	scheme_template=$(cat "cold_mem_stat_damos_template_for_wmarks.json")

	# Test high watermark-based deactivation
	ensure_free_mem_ratio 990 100
	if [ "$?" -ne 0 ]
	then
		return
	fi
	applied=42

	scheme=$(echo "$scheme_template" | \
		sed "s/wmarks_high_to_be_replaced/50/" | \
		sed "s/wmarks_mid_to_be_replaced/40/" | \
		sed "s/wmarks_low_to_be_replaced/30/")

	measure_scheme_applied "$scheme" "paddr" 3 \
		"$damon_interface"
	if [ "$applied" -ne 0 ]
	then
		echo "FAIL $testname (high watermark doesn't works)"
		exit 1
	fi

	# Test mid-low watermarks-based activation
	ensure_free_mem_ratio 990 100
	if [ "$?" -ne 0 ]
	then
		return
	fi
	applied=0

	scheme=$(echo "$scheme_template" | \
		sed "s/wmarks_high_to_be_replaced/999/" | \
		sed "s/wmarks_mid_to_be_replaced/995/" | \
		sed "s/wmarks_low_to_be_replaced/100/")

	measure_scheme_applied "$scheme" "paddr" 3 \
		"$damon_interface"
	if [ "$applied" -le 0 ]
	then
		echo "FAIL $testname (mid watermark doesn't works)"
		exit 1
	fi

	# Test low watermark-based deactivation
	ensure_free_mem_ratio 990 100
	if [ "$?" -ne 0 ]
	then
		return
	fi
	applied=42

	scheme=$(echo "$scheme_template" | \
		sed "s/wmarks_high_to_be_replaced/999/" | \
		sed "s/wmarks_mid_to_be_replaced/998/" | \
		sed "s/wmarks_low_to_be_replaced/995/")

	measure_scheme_applied "$scheme" "paddr" 3 \
		"$damon_interface"
	if [ "$applied" -ne 0 ]
	then
		echo "FAIL $testname (low watermark doesn't works)"
		exit 1
	fi

	echo "PASS $testname"
}

test_filters() {
	testname="schemes-filters $damon_interface"

	nr_swap_devs=$(( $(wc -l /proc/swaps | awk '{print $1}') - 1 ))
	if [ "$nr_swap_devs" -eq 0 ]
	then
		echo "SKIP $testname (no swap)"
		return
	fi

	workload="alloc_1gb_spin"
	workload_src="${workload}.c"
	if ! gcc -o "$workload" "$workload_src"
	then
		echo "FAIL $testname ($workload compile failed)"
		exit 1
	fi

	prcl_damos_json="prcl_damos.json"
	sudo "$damo" start -c "$prcl_damos_json" 2> /dev/null
	"./$workload" &
	workload_pid=$!
	sleep 5
	rss=$(ps -o rss=, --pid "$workload_pid")
	if [ "$rss" -gt 500000 ]
	then
		echo "FAIL $testname (prcl doesn't work: $rss)"
		exit 1
	fi
	kill -9 "$workload_pid"
	sudo "$damo" stop 2> /dev/null

	prcl_no_anon_damos_json="prcl_no_anon_damos.json"
	sudo "$damo" start -c "$prcl_no_anon_damos_json" 2> /dev/null
	"./$workload" &
	workload_pid=$!
	sleep 5
	rss=$(ps -o rss=, --pid "$workload_pid")
	if [ "$rss" -lt 800000 ]
	then
		echo "FAIL $testname (prcl_no_anon doesn't work: $rss)"
		exit 1
	fi
	kill -9 "$workload_pid"
	sudo "$damo" stop 2> /dev/null

	cgroup="/sys/fs/cgroup/unified/"
	memcg_support="false"
	for controller in $(sudo cat "$cgroup/cgroup.controllers")
	do
		if [ "$controller" = "memory" ]
		then
			memcg_support="true"
			break
		fi
	done
	if [ "$memcg_support" = "false" ]
	then
		echo "SKIP $testname (memcg not supported)"
		return
	fi
	echo "+memory" | sudo tee "$cgroup/cgroup.subtree_control" > /dev/null
	sudo mkdir "$cgroup/damos_filtered"
	echo $$ | sudo tee "$cgroup/damos_filtered/cgroup.procs" > /dev/null

	prcl_no_cgroup_damos_json="prcl_no_cgroup_damos.json"
	sudo "$damo" start -c "$prcl_no_cgroup_damos_json" 2> /dev/null
	"./$workload" &
	workload_pid=$!
	sleep 5
	rss=$(ps -o rss=, --pid "$workload_pid")
	if [ "$rss" -lt 800000 ]
	then
		echo "FAIL $testname (prcl_no_cgroup doesn't work: $rss)"
		exit 1
	fi
	kill -9 "$workload_pid"
	sudo "$damo" stop 2> /dev/null
	for pid in $(cat "$cgroup/damos_filtered/cgroup.procs")
	do
		# echo "move pid $pid"
		echo "$pid" | sudo tee "$cgroup/cgroup.procs" > /dev/null
	done
	rmdir "$cgroup/damos_filtered"

	echo "PASS $testname"
}

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
	if ! sudo "$damo" features supported \
	       --damon_interface "$damon_interface" 2> /dev/null | \
	       grep -w "schemes" > /dev/null
	then
		echo "SKIP $(basename $(pwd))"
		exit 0
	fi

	test_stat "$damon_interface"
	test_wmarks "$damon_interface"

	if sudo "$damo" features supported \
	       --damon_interface "$damon_interface" 2> /dev/null | \
		grep -w "schemes_filters" > /dev/null
	then
		test_filters
	fi
done

echo "PASS $(basename $(pwd))"
