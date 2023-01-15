#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse

import _damo_schemes_input
import _damon
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

    intervals = _damon.DamonIntervals(args.sample, args.aggr, args.aggr)

    lines = []
    damos_list, err = _damo_schemes_input.damo_schemes_to_damos(args.input)
    if err:
        print('cannot create damos from argument (%s)' % err)
        exit(1)
    for damos in damos_list:
        lines.append(
                _damon_dbgfs.damos_to_debugfs_input(damos, intervals,
                    args.scheme_version))
    print ('\n'.join(lines))

if __name__ == '__main__':
    main()
