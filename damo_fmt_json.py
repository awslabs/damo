# SPDX-License-Identifier: GPL-2.0

"""
Convert args to DAMON json input.
"""

import argparse
import json

import _damon
import _damon_args

def set_argparser(parser):
    _damon_args.set_argparser(parser, add_record_options=False)
    parser.add_argument('--raw', action='store_true',
            help='print numbers in machine friendly raw form')

def main(args=None):
    if not args:
        parser = set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_permission()

    kdamonds, err = _damon_args.kdamonds_for(args)
    if err:
        print('invalid arguments (%s)' % err)
        exit(1)
    print(json.dumps({'kdamonds': [k.to_kvpairs(args.raw) for k in kdamonds]},
        indent=4))

if __name__ == '__main__':
    main()
