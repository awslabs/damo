#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

damo="../../damo"

BINDIR=$(dirname "$0")
cd "$BINDIR" || exit 1

test_report() {
	cmd=$1
	test_name=$2

	expected=$(realpath "expects/report-$test_name")
	result=$(realpath "results/report-$test_name")

	eval "python3 $cmd" > "$result" 2> /dev/null
	if ! diff -q "$expected" "$result"
	then
		echo "FAIL report-$test_name"
		exit 1
	fi
	echo "PASS report-$test_name"
}

mkdir -p results

test_report "$damo report raw" "raw"

test_report "$damo report raw -i damon.data.json_compressed" "raw"

test_report \
	"$damo report raw -i perf.data.script" \
	"raw_perf_script"

test_report "$damo report wss -r 1 101 1 --raw_number" "wss"

test_report "$damo report wss -r 1 101 1 --work_time 1000000 --raw_number" \
	"wss_worktime_1s"

test_report \
	"$damo adjust --aggregate_interval 1000000 && \
	$damo report raw -i damon.adjusted.data" \
	"aggr_1s_raw"

test_report \
	"$damo adjust --skip 30 --aggregate_interval 1000000 && \
	$damo report raw -i damon.adjusted.data" \
	"aggr_1s_raw_skip_30"

test_report "$damo report nr_regions -r 1 101 1" "nr_regions"

test_report "$damo report heats --guide" "heats_guide"
test_report "$damo report heatmap --guide" "heats_guide"

test_report "$damo report heats" "heats"
test_report "$damo report heatmap --output raw" "heats"

rm -fr results damon.adjusted.data

echo "PASS" "$(basename "$(pwd)")"
