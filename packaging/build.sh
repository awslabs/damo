#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

if [ $# -lt 2 ]
then
	echo "Usage: $0 <work dir> <version> [--force]"
	exit 1
fi

work_dir=$1
version=$2

rm_workdir="false"
if [ $# -eq 3 ] && [ "$3" = "--force" ]
then
	rm_workdir="true"
fi

if [ -d "$work_dir" ] || [ -f "$work_dir" ]
then
	echo "$work_dir already exist"
	if [ "$rm_workdir" = "false" ]
	then
		exit 1
	fi

	echo "remove it for clean build"
	if ! rm -fr "$work_dir"
	then
		echo "failed removing old $work_dir"
		exit 1
	fi
fi

mkdir "$work_dir"
bindir=$(dirname "$0")

for file in "setup.py" "pyproject.toml"
do
	cp -p "$bindir/$file" "$work_dir/"
done

"$bindir/mk_readme.sh" "$work_dir" "$version"

damo_dir="$bindir/.."

mkdir -p "$work_dir/src/damo"
cp -p "$damo_dir/src/"*.py "$work_dir/src/damo"
touch "$work_dir/src/damo/__init__.py"

cd "$work_dir"
if python3 -m build
then
	echo
	echo "The distribution archives are ready at $work_dir/dist/"
	echo "You may upload it now via:"
	echo "    cd $work_dir && python3 -m twine upload dist/*"
fi
