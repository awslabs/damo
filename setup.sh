#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

K_VERSION=$(uname -r)

# Usage of This file
usage() {
	cat <<EOF
Usage: $0 [OPTIONS]

Description:
	This is a setup script which will check & install deps required for damon
	Builds and install the perf-tool for your custom kernel.

OPTIONS:
  -h, --help	Gives out info about how to use this file

EOF
}

# Check if this kernel has CONFIG_DAMON enabled. If not exit
check_damon() { 
	if zgrep -q "CONFIG_DAMON=y" /boot/config-$K_VERSION; then 
		echo "DAMON is ENABLED on this kernel."
	else
		echo "Please reconfigure this kernel & enable DAMON CONFIG_DAMON=y"
		exit 0
	fi
}

# Install perf at /usr/local for custom kernel
perf_install() {
	echo
	read -p "Enter the path of kernel $K_VERSION"$'\n' kpath
	kpath=$(eval "echo $kpath")
	kpath=$(realpath "$kpath")
	cd $kpath
	if [ -d "tools/perf" ]; then
		cd tools/perf
		sudo make
		sudo make prefix=/usr/local install
		if [ $? == 0 ]; then
			echo "Perf `perf -v` has been installed for `uname -r` kernel"
		else
			"Perf isn't installed correctly"
			exit 0
		fi
	else
		echo "Path doesn't exist something's wrong"
	fi
}

# Install all required dependencies for perf tool
perf_deps() {
sudo apt install libslang2-dev \
		 libcap-dev    \
		 libperl-dev   \
		 libbabeltrace-dev \
		 libpfm4-dev	\
		 libtraceevent-dev \
		 clang	\
		 asciidoc  \
		 pkg-config \
		 libnuma-dev \
		 libzstd-dev \
		 libpfm4-dev \
		 libunwind-dev \
		 systemtap-sdt-dev \
		 openjdk-8-jdk
}

if [[ $# -gt 1 || $@ == "--help" || $@ == "-h" ]]; then
	usage
	exit 0
fi

check_damon
perf_deps
perf_install
