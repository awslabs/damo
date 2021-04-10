#!/bin/bash

BINDIR=$(dirname "$0")
cd "$BINDIR" || exit 1

test_report() {
	cmd=$1
	test_name=$2

	expected="$test_name""_before"
	result="$test_name""_after"

	eval "$cmd" > "$result"
	diff -q "$expected" "$result"
	if [ $? -ne 0 ]
	then
		echo "report-$test_name FAIL"
		exit 1
	fi
	echo "report-$test_name PASS"
}

test_report "../damo report raw" "raw"

test_report \
	"../damo report raw --input_type perf_script -i perf_script_output" \
	"raw_perf_script"

test_report "../damo report wss -r 1 101 1" "wss"

test_report "../damo report wss -r 1 101 1 --work_time 1000000" \
	"wss_worktime_1s"

test_report \
	"../adjust.py 1000000 && ../damo report raw -i damon.adjusted.data" \
	"aggr_1s_raw"

test_report "../damo report nr_regions -r 1 101 1" "nr_regions"

test_report "../damo report heats --guide" "heats_guide"

test_report "../damo report heats" "heats"

if perf script -l | grep -q damon
then
	test_report "perf script report damon -i perf.data heatmap" \
		"perf_heatmap"
fi

rm *_after

echo "PASS"
