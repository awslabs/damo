#!/bin/bash

bindir=$(dirname "$0")
cd "$bindir"

testname=$(basename $(pwd))

sysdir="/sys/module/damon_reclaim/parameters"

if [ ! -d "$sysdir" ]
then
	echo "SKIP $testname (the sys dir not found)"
	exit
fi

enabled=$(sudo cat "$sysdir/enabled")
if [ "$enabled" = "N" ] && pgrep kdamond > /dev/null
then
	echo "FAIL damon_reclaim (disabled but kdamond running)"
	exit 1
fi

if [ "$enabled" = "Y" ] && ! pgrep kdamond > /dev/null
then
	echo "FAIL damon_reclaim (enabled but kdamond not running)"
	exit 1
fi

echo "PASS $testname"
