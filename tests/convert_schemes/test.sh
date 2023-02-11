#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

bindir=$(dirname "$0")
cd "$bindir"

test_convert_file() {
	for input in ./inputs/*
	do
		for version in {0..4}
		do
			scheme_name=$(basename "$input")

			expected=$(cat "./expects/$scheme_name.v$version")
			converted=$(../../_damo_schemes_to_dbgfs_input.py \
				--scheme_version "$version" "$input" \
				2> /dev/null)
			if [ ! "$expected" = "$converted" ]
			then
				echo "FAIL convert-schemes (for $input, $version)"
				exit 1
			fi
		done
	done
	echo "PASS convert_schemes-file"
}

test_convert_txt() {
	for input_file in ./inputs/*
	do
		for version in {0..4}
		do
			scheme_name=$(basename "$input_file")
			expected=$(cat "./expects/$scheme_name.v$version")

			input_txt=$(cat "$input_file")
			converted=$(../../_damo_schemes_to_dbgfs_input.py \
				--scheme_version "$version" "$input_txt" \
				2> /dev/null)
			if [ ! "$expected" = "$converted" ]
			then
				echo "FAIL convert-schemes (for $input_file)"
				exit 1
			fi
		done
	done
	echo "PASS convert_schemes-txt"
}

test_convert_file
test_convert_txt

echo "PASS $(basename $(pwd))"
