#!/bin/bash

BINDIR=$(dirname "$0")
cd "$BINDIR" || exit 1

do_test() {
	cmd=$1
	name=$2

	filename=$(echo "$name" | awk -F'report-' '{print $2}')
	expected="$filename""_before"
	result="$filename""_after"

	eval "$cmd" > "$result"
	diff -q "$expected" "$result"
	if [ $? -ne 0 ]
	then
		echo "$name FAIL"
		exit 1
	fi
	echo "$name PASS"
}

do_test "../damo report raw" "report-raw"

do_test "../damo report raw --input_type perf_script -i perf_script_output" \
	"report-raw_perf_script"

do_test "../damo report wss -r 1 101 1" "report-wss"

do_test "../damo report wss -r 1 101 1 --work_time 1000000" \
	"report-wss_worktime_1s"

do_test "../adjust.py 1000000 && ../damo report raw -i damon.adjusted.data" \
	"report-aggr_1s_raw"

do_test "../damo report nr_regions -r 1 101 1" "report-nr_regions"

do_test "../damo report heats --guide" "report-heats_guide"

do_test "../damo report heats" "report-heats"

if perf script -l | grep -q damon
then
	do_test "perf script report damon -i perf.data heatmap" \
		"report-perf_heatmap"
fi

rm *_after

echo "PASS"
