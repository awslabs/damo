#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

bindir=$(dirname "$0")
cd "$bindir"

damon_debugfs="/sys/kernel/debug/damon"
damo="../../damo"

cleanup_files()
{
	files_to_remove="./damon.data ./damon.data.perf.data"
	for file in $files_to_remove
	do
		if [ -f "$file" ]
		then
			if ! rm "$file"
			then
				echo "removing $file failed"
				exit 1
			fi
		fi
	done
}

test_leave_perf_data()
{
	if ! sudo "$damo" record "sleep 2" --leave_perf_data
	then
		echo "FAIL record-leave-perf-data (damo-record command failed)"
		exit 1
	fi

	if [ ! -f ./damon.data.perf.data ]
	then
		echo "FAIL record-leave-perf-data (perf.data not found)"
		exit 1
	fi

	cleanup_files

	echo "PASS record-leave-perf-data"
}

test_record_validate()
{
	if [ $# -ne 2 ]
	then
		echo "Usage: $0 <target> <timeout>"
		exit 1
	fi

	target=$1
	timeout=$2

	if [ "$target" = "paddr" ] && ! sudo "$damo" features supported | \
		grep -w paddr > /dev/null
	then
		echo "SKIP record-validate $target $timeout (paddr unsupported)"
		return
	fi

	sudo timeout "$timeout" "$damo" record "$target"
	rc=$?
	if [ $? -ne 0 ] && [ $? -ne 124 ]
	then
		echo "FAIL record-validate $target $timeout"
		echo "(damo-record command failed with value $rc)"
		exit 1
	fi

	if ! "$damo" validate
	then
		echo "FAIL record-validate (record fild is not valid)"
		exit 1
	fi

	if [ -f ./damon.data.perf.data ]
	then
		echo "FAIL record-validate (perf.data is not removed)"
		exit 1
	fi

	cleanup_files

	echo "PASS record-validate \"$target\" $timeout"
}

if [ ! -d /sys/kernel/debug/damon ]
then
	echo "SKIP $(basename $(pwd)) (DAMON debugfs not found)"
	exit 0
fi

test_record_validate "sleep 3" 4
test_record_validate "paddr" 3
test_leave_perf_data

echo "PASS $(basename $(pwd))"
