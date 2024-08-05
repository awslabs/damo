# SPDX-License-Identifier: GPL-2.0

import collections
import json

import _damo_yaml
import _damo_records
import damo_args_damon

def main(args):
    filter_, err = _damo_records.args_to_filter(args)
    if err is not None:
        print('converting arguments to filter failed (%s)' % err)
        exit(1)
    kvpairs = filter_.to_kvpairs(args.raw)

    if args.format == 'json':
        print(json.dumps(kvpairs, indent=4))
    elif args.format == 'yaml':
        text, err = _damo_yaml.dump(kvpairs)
        if err is not None:
            print('yaml dump failed (%s)' % err)
            exit(1)
        print(text)

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
