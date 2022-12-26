#!/usr/bin/env python
# SPDX-License-Identifier: GPL-2.0

"""
Convert args to DAMON json input.
"""

import argparse
import json

import _damon_args

def set_argparser(parser):
    _damon_args.set_explicit_target_argparser(parser)
    parser.add_argument('--raw', action='store_true',
            help='print numbers in machine friendly raw form')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    kdamonds = [k.to_kvpairs(args.raw) for k in
            _damon_args.kdamonds_from_damon_args(args)]
    print(json.dumps(kdamonds, indent=4))

if __name__ == '__main__':
    main()
