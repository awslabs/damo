#!/bin/bash

bindir=$(dirname "$0")
cd "$bindir"

damon_debugfs="/sys/kernel/debug/damon"
damo="../../damo"

test_convert() {
	for input in ./inputs/*
	do
		scheme_name=$(basename "$input")

		expected=$(cat "./expects/$scheme_name")
		converted=$(../../_convert_damos.py "$input")
		if [ ! "$expected" = "$converted" ]
		then
			echo "FAIL convert-schemes (for $input)"
			exit 1
		fi
	done
}

test_convert

echo "PASS $(basename $(pwd))"
