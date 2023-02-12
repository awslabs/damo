#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

bindir=$(dirname "$0")
cd "$bindir" || exit 1

for test_dir in unit record report schemes \
	damon_reclaim damon_lru_sort start_stop
do
	if ! "./$test_dir/test.sh"
	then
		exit 1
	fi
done

echo "PASS ALL"
