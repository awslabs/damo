#!/usr/bin/env python
# SPDX-License-Identifier: GPL-2.0

"""
Convert old damos schemes to json format.
"""

import argparse
import json

import _damon_args_schemes

def set_argparser(parser):
    parser.add_argument('schemes', metavar='<file or string>',
            help='schemes in old .damos format')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    schemes, err = _damon_args_schemes.schemes_option_to_damos(args.schemes)
    if err:
        print('failed --schemes parsing (%s)' % err)
        exit(1)
    print(json.dumps([scheme.to_kvpairs() for scheme in schemes], indent=4))

if __name__ == '__main__':
    main()
