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
	if ! sudo "$damo" record "sleep 3"
	then
		echo "FAIL record-validate (damo-record command failed)"
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

	echo "PASS record-validate-sleep-3"
}

test_record_validate
test_leave_perf_data

echo "PASS $(basename $(pwd))"
