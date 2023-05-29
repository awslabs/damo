# SPDX-License-Identifier: GPL-2.0

"""
Convert old damos schemes to json format.
"""

import argparse
import json

import _damo_deprecated

def set_argparser(parser):
    parser.add_argument('schemes', metavar='<file or string>',
            help='schemes in old .damos format')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damo_deprecated.avoid_crashing_single_line_scheme_for_testing = True
    _damo_deprecated.avoid_crashing_v1_v3_schemes_for_testing = True
    schemes, err = _damo_deprecated.damo_single_line_schemes_to_damos(
            args.schemes)
    if err:
        print('failed --schemes parsing (%s)' % err)
        exit(1)
    print(json.dumps([scheme.to_kvpairs() for scheme in schemes], indent=4))

if __name__ == '__main__':
    main()
