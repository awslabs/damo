# SPDX-License-Identifier: GPL-2.0

import collections
import json
import sys

try:
    import yaml
except ModuleNotFoundError as e:
    # do nothing.  The yaml using functions should handle the exception
    # properly.
    pass

import _damo_records
import damo_args_damon

def main(args):
    if args.format == 'yaml':
        if not 'yaml' in sys.modules:
            print('yaml module import failed')
            exit(1)

    filter_, err = _damo_records.args_to_filter(args)
    if err is not None:
        print('converting arguments to filter failed (%s)' % err)
        exit(1)
    kvpairs = filter_.to_kvpairs(args.raw)

    if args.format == 'json':
        print(json.dumps(kvpairs, indent=4))
    elif args.format == 'yaml':
        print(yaml.dump(kvpairs))

def set_argparser(parser):
    parser.description = ' '.join([
        'format DAMON monitoring results parser parameters'])
    _damo_records.set_filter_argparser(parser)
    parser.add_argument(
            '--format', choices=['json', 'yaml'], default='json',
            help='format of the output')
    parser.add_argument(
            '--raw', action='store_true',
            help='print numbers in machine friendly raw form')
