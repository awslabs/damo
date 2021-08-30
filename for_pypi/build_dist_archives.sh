#!/bin/bash

if [ $# -ne 1 ]
then
	echo "Usage: $0 <work dir>"
	exit 1
fi

work_dir=$1
damo_dir="$1/.."

if [ -d "$work_dir" ] || [ -f "$work_dir" ]
then
	echo "$work_dir already exist"
	exit 1
fi

mkdir "$work_dir"
bindir=$(dirname "$0")

for file in "README.md" "setup.py" "pyproject.toml"
do
	cp "$bindir/$file" "$work_dir/"
done

mkdir -p "$work_dir/src/damo"
cp "$damo_dir/"*.py "$work_dir/src/damo"
cp "$damo_dir/damo" "$work_dir/src/damo/damo.py"
touch "$work_dir/src/damo/__init__.py"

cd "$work_dir"
if python3 -m build
then
	echo
	echo "The distribution archives are ready at $work_dir/dist/"
	echo "You may upload it now via:"
	echo "    python3 -m twine upload dist/*"
fi
