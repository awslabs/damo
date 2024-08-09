# SPDX-License-Identifier: GPL-2.0

import collections
import json

import _damo_yaml
import _damon
import _damon_args

def main(args):
    _damon.ensure_root_permission()

    kdamonds, err = _damon_args.kdamonds_for(args)
    if err:
        print('invalid arguments (%s)' % err)
        exit(1)

    for k in kdamonds:
        for c in k.contexts:
            for s in c.schemes:
                s.stats = None
                s.tried_regions = None

    kvpairs = {'kdamonds': [k.to_kvpairs(args.raw) for k in kdamonds]}
    if args.format == 'json':
        print(json.dumps(kvpairs, indent=4))
    elif args.format == 'yaml':
        text, err = _damo_yaml.dump(kvpairs)
        if err is not None:
            print('yaml dump failed (%s)' % err)
            exit(1)
        print(text)

def set_argparser(parser):
    _damon_args.set_argparser(parser, add_record_options=False, min_help=False)
    parser.description = ' '.join([
        'format DAMON parameters'])
    parser.add_argument(
            '--format', choices=['json', 'yaml'], default='json',
            help='format of the output')
    parser.add_argument(
            '--raw', action='store_true',
            help='print numbers in machine friendly raw form')
