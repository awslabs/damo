#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

bindir=$(dirname "$0")
cd "$bindir"

damo="../../damo"

testname=$(basename $(pwd))

damon_interfaces=""

if [ -d "/sys/kernel/mm/damon" ]
then
	damon_interfaces+="sysfs "
fi

if [ "$damon_interfaces" = "" ]
then
	echo "SKIP $(basename $(pwd)) (DAMON interface not found)"
	exit 0
fi

for damon_interface in $damon_interfaces
do
	testname2="$testname $damon_interface"
	sudo "$damo" start --ops paddr --damon_interface "$damon_interface" \
		-c monitoring_damos.json 2> /dev/null
	if ! pgrep kdamond.0 > /dev/null
	then
		echo "FAIL $testname2 (kdamond.0 pid not found after start)"
		exit 1
	fi
	echo "PASS $testname2 start"

	sudo timeout 3 "$damo" record ongoing \
		--damon_interface "$damon_interface" &> /dev/null
	if ! "$damo" validate 2> /dev/null
	then
		echo "FAIL $testname2 (invalid record file)"
		if ! sudo "$damo" stop
		then
			echo "failed stopping DAMON"
		fi
		exit 1
	fi
	echo "PASS $testname2 record-ongoing-validate"

	for i in {1..10}
	do
		if ! sudo "$damo" status &> /dev/null
		then
			echo "FAIL $testname2 status $i failed"
			if ! sudo "$damo" stop
			then
				echo "failed stopping DAMON"
			fi
			exit 1
		fi
	done
	echo "PASS $testname2 status $i"

	for i in {1..10}
	do
		if ! sudo "$damo" show &> /dev/null
		then
			echo "FAIL $testname2 show $i failed"
			if ! sudo "$damo" stop
			then
				echo "failed stopping DAMON"
			fi
			exit 1
		fi
	done
	echo "PASS $testname2 show $i"

	if ! sudo "$damo" tune --aggr 200000 --ops paddr \
		--damon_interface "$damon_interface" &> /dev/null
	then
		echo "FAIL $testname2 tune"
		if ! sudo "$damo" stop
		then
			echo "failed stopping DAMON"
		fi

		exit 1
	fi
	sudo timeout 3 "$damo" record ongoing \
		--damon_interface "$damon_interface" &> /dev/null
	if ! "$damo" validate --aggr 180000 220000 2> /dev/null
	then
		echo "FAIL $testname2 (invalid record file after tune)"
		if ! sudo "$damo" stop
		then
			echo "failed stopping DAMON"
		fi
		exit 1
	fi
	echo "PASS $testname2 tune-record-ongoing-validate"

	sudo "$damo" stop --damon_interface "$damon_interface" 2> /dev/null
	if pgrep kdamond.0 > /dev/null
	then
		echo "FAIL $testname2 (kdamond.0 pid found after stop)"
		exit 1
	fi
	echo "PASS $testname2 stop"
done

rm -f damon.data damon.data.old

echo "PASS $(basename $(pwd))"
