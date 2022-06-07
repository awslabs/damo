#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

bindir=$(dirname "$0")
cd "$bindir"

testname=$(basename $(pwd))

sysdir="/sys/module/damon_lru_sort/parameters"

if [ ! -d "$sysdir" ]
then
	echo "SKIP $testname (the sys dir not found)"
	exit
fi

if [ ! -f "$sysdir/kdamond_pid" ]
then
	echo "SKIP $testname (kdamond_pid file not found)"
	exit
fi

enabled=$(sudo cat "$sysdir/enabled")
kdamond_pid=$(sudo cat "$sysdir/kdamond_pid")
if [ "$enabled" = "N" ] && [ "$kdamond_pid" -ne -1 ]
then
	echo "FAIL $testname (disabled but kdamond running)"
	exit 1
fi

if [ "$enabled" = "Y" ] && [ "$kdamond_pid" -eq -1 ]
then
	echo "FAIL $testname (enabled but kdamond not running)"
	exit 1
fi

echo N | sudo tee "$sysdir/enabled" > /dev/null && sleep 7
if [ "$(sudo cat "$sysdir/kdamond_pid")" -ne -1 ]
then
	echo "FAIL $testname (disabling failed)"
	exit 1
fi

echo Y | sudo tee "$sysdir/enabled" > /dev/null && sleep 2
kdamond_pid=$(sudo cat "$sysdir/kdamond_pid")
if [ "$kdamond_pid" -eq -1 ]
then
	echo "FAIL $testname (enabling failed)"
	exit 1
fi
if ! ps --pid  "$kdamond_pid" > /dev/null
then
	echo "FAIL $testname (kdamond not started)"
	exit 1
fi

echo N | sudo tee "$sysdir/enabled" > /dev/null && sleep 7
kdamond_pid=$(sudo cat "$sysdir/kdamond_pid")
if [ "$kdamond_pid" -ne -1 ]
then
	echo "FAIL $testname (disabling again failed: $kdamond_pid)"
	exit 1
fi


echo "PASS $testname"
