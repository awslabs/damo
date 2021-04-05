#!/bin/bash

BINDIR=$(dirname "$0")
cd "$BINDIR" || exit 1

../damo report raw > raw_after
diff -q raw_before raw_after
if [ $? -ne 0 ]
then
	echo "report-raw FAIL"
	exit 1
fi
echo "report-raw PASS"

../damo report raw --input_type perf_script -i perf_script_output \
	> raw_perf_script_after
diff -q raw_perf_script_before raw_perf_script_after
if [ $? -ne 0 ]
then
	echo "report-raw --perf_script FAIL"
	exit 1
fi
echo "report-raw --perf_script PASS"

../damo report wss -r 1 101 1 > wss_after
diff -q wss_before wss_after
if [ $? -ne 0 ]
then
	echo "report-wss FAIL"
	exit 1
fi
echo "report-wss PASS"

../adjust.py 1000000
../damo report raw -i damon.adjusted.data > aggr_1s_raw_after
diff -q aggr_1s_raw_before aggr_1s_raw_after
if [ $? -ne 0 ]
then
	echo "adjust FAIL"
	exit 1
fi
echo "adjust PASS"

../damo report nr_regions -r 1 101 1 > nr_regions_after
diff -q nr_regions_before nr_regions_after
if [ $? -ne 0 ]
then
	echo "report-nr_regions FAIL"
	exit 1
fi
echo "report-nr_regions PASS"

../damo report heats --guide > heats_guide_after
diff -q heats_guide_before heats_guide_after
if [ $? -ne 0 ]
then
	echo "report-heats-guide FAIL"
	exit 1
fi
echo "report-heats-guide PASS"

../damo report heats > heats_after
diff -q heats_before heats_after
if [ $? -ne 0 ]
then
	echo "report-heats FAIL"
	exit 1
fi
echo "report-heats PASS"

if perf script -l | grep -q damon
then
	perf script report damon -i perf.data heatmap > perf_heatmap_after
	diff -q perf_heatmap_before perf_heatmap_after
	if [ $? -ne 0 ]
	then
		echo "perf-damon-heatmap FAIL"
		exit 1
	fi
	echo "perf-damon-heatmap PASS"
fi

rm *_after

echo "PASS"
