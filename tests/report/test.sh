#!/bin/bash

damo="../../damo"

BINDIR=$(dirname "$0")
cd "$BINDIR" || exit 1

test_report() {
	cmd=$1
	test_name=$2

	expected="expects/report-$test_name"
	result="results/report-$test_name"

	eval "$cmd" > "$result"
	if ! diff -q "$expected" "$result"
	then
		echo "FAIL report-$test_name"
		exit 1
	fi
	echo "PASS report-$test_name"
}

mkdir -p results

test_report "$damo report raw" "raw"

test_report \
	"$damo report raw --input_type perf_script -i perf.data.script" \
	"raw_perf_script"

test_report "$damo report wss -r 1 101 1 --raw_number" "wss"

test_report "$damo report wss -r 1 101 1 --work_time 1000000 --raw_number" \
	"wss_worktime_1s"

test_report \
	"$damo adjust 1000000 && $damo report raw -i damon.adjusted.data" \
	"aggr_1s_raw"

test_report "$damo report nr_regions -r 1 101 1" "nr_regions"

test_report "$damo report heats --guide" "heats_guide"

test_report "$damo report heats" "heats"

rm -fr results

echo "PASS" "$(basename "$(pwd)")"
