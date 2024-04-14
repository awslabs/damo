#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

bindir=$(dirname "$0")
cd "$bindir"

damo="../../damo"

cleanup_files()
{
	files_to_remove="./damon.data ./damon.data.perf.data ./damon.data.old"
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

test_record_permission()
{
	sudo timeout 3 "$damo" record "sleep 3" --output_permission 611 \
		&> /dev/null
	if [ ! "$(stat -c %a damon.data)" = "611" ]
	then
		echo "FAIL record-permission"
		exit 1
	fi
	cleanup_files

	echo "PASS record-permission"
}

test_record_validate()
{
	if [ $# -ne 4 ]
	then
		echo "Usage: $0 <target> <timeout> <region> \\"
		echo "		<damon interface to use>"
		exit 1
	fi

	target=$1
	timeout=$2
	regions_boundary=$3
	damon_interface=$4

	testname="record-validate \"$target\" $timeout $regions_boundary"
	testname+=" $damon_interface"

	if [ "$target" = "paddr" ] && ! sudo "$damo" features \
		--damon_interface_DEPRECATED "$damon_interface" supported \
		2> /dev/null | \
		grep -w paddr &> /dev/null
	then
		echo "SKIP record-validate $target $timeout (paddr unsupported)"
		return
	fi

	if [ "$regions_boundary" = "none" ]
	then
		sudo timeout "$timeout" "$damo" record "$target" \
			--damon_interface_DEPRECATED "$damon_interface" \
			&> /dev/null
	else
		sudo timeout "$timeout" "$damo" record "$target" \
			--regions "$regions_boundary" \
			--damon_interface_DEPRECATED "$damon_interface" \
			&> /dev/null
	fi

	rc=$?
	if [ $rc -ne 0 ] && [ $rc -ne 124 ]
	then
		echo "FAIL $testname"
		echo "(damo-record command failed with value $rc)"
		exit 1
	fi

	if [ "$regions_boundary" = "none" ]
	then
		if ! "$damo" validate &> /dev/null
		then
			echo "FAIL $testname (record file is not valid)"
			exit 1
		fi
	else
		if ! "$damo" validate --regions_boundary "$regions_boundary" \
			&> /dev/null
		then
			echo "FAIL $testname (record file is not valid)"
			exit 1
		fi
	fi

	if [ -f ./damon.data.perf.data ]
	then
		echo "FAIL $testname (perf.data is not removed)"
		exit 1
	fi

	permission=$(stat -c %a damon.data)
	if [ ! "$permission" = "600" ]
	then
		echo "FAIL $testname (out file permission $permission)"
		exit 1
	fi

	cleanup_files

	echo "PASS $testname"
}

damon_interfaces=""
if [ -d "/sys/kernel/debug/damon" ]
then
	damon_interfaces+="debugfs "
fi

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
	test_record_validate "sleep 3" 4 "none" "$damon_interface"
	test_record_validate "paddr" 3 "none" "$damon_interface"
done

if sudo "$damo" features \
	--damon_interface_DEPRECATED "$damon_interface" supported \
	2> /dev/null | \
	grep -w fvaddr &> /dev/null
then
	test_record_validate "sleep 3" 4 "4096-81920" "sysfs"
fi

test_record_permission

echo "PASS $(basename $(pwd))"
