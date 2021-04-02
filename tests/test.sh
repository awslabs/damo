#!/bin/bash

BINDIR=$(dirname "$0")
cd "$BINDIR" || exit 1

../damo report raw > raw_after
diff raw_before raw_after
if [ $? -ne 0 ]
then
	echo "report-raw FAIL"
	exit 1
fi

../damo report wss -r 1 101 1 > wss_after
diff wss_before wss_after
if [ $? -ne 0 ]
then
	echo "report-wss FAIL"
	exit 1
fi

../adjust.py 1000000
../damo report raw -i damon.adjusted.data > aggr_1s_raw_after
diff aggr_1s_raw_before aggr_1s_raw_after
if [ $? -ne 0 ]
then
	echo "adjust FAIL"
	exit 1
fi

../damo report nr_regions -r 1 101 1 > nr_regions_after
diff nr_regions_before nr_regions_after
if [ $? -ne 0 ]
then
	echo "report-nr_regions FAIL"
	exit 1
fi

rm *_after

echo "PASS"
