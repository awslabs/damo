#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

if [ $# -ne 2 ]
then
	echo "Usage: $0 <work dir> <version>"
	exit 1
fi

work_dir=$1
version=$2
bindir=$(dirname "$0")

readme_original="$bindir/../README.md"
readme=$work_dir/README.md
cp "$readme_original" "$readme"

# PyPi doesn't support gif
sed -i '/water_nsquared.gif/d' "$readme"

# Change images addresses
sed -i "s/images\/masim_zigzag_heatmap_ascii.png/https:\/\/raw.githubusercontent.com\/damonitor\/damo\/$version\/images\/masim_zigzag_heatmap_ascii.png/" "$readme"
sed -i "s/images\/masim_stairs_heatmap_ascii.png/https:\/\/raw.githubusercontent.com\/damonitor\/damo\/$version\/images\/masim_stairs_heatmap_ascii.png/" "$readme"

# Change CONTRIBUTING
sed -i "s/(USAGE.md)/(https:\/\/github.com\/damonitor\/damo\/blob\/$version\/USAGE.md)/" "$readme"
