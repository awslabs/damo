#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse

import _damo_schemes_input
import _damon_dbgfs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', metavar='<file or schemes in text>',
            help='input file describing the schemes or the schemes')
    parser.add_argument('-s', '--sample', metavar='<interval>', type=int,
            default=5000, help='sampling interval (us)')
    parser.add_argument('-a', '--aggr', metavar='<interval>', type=int,
            default=100000, help='aggregation interval (us)')
    parser.add_argument('--scheme_version', metavar='<version>', type=int,
            choices=range(0, 5), default=4, help='destination scheme version')
    args = parser.parse_args()

    sample_interval = args.sample
    aggr_interval = args.aggr
    scheme_ver = args.scheme_version

    lines = []
    for damos in _damo_schemes_input.damo_schemes_to_damos(args.input):
        lines.append(
                _damon_dbgfs.damos_to_debugfs_input(damos, sample_interval,
                    aggr_interval, scheme_ver))
    print ('\n'.join(lines))

if __name__ == '__main__':
    main()
