# SPDX-License-Identifier: GPL-2.0

import json

import _damon
import _damon_args

def pr_json(kdamonds, raw):
    for k in kdamonds:
        for c in k.contexts:
            for s in c.schemes:
                s.stats = None
                s.tried_regions = None

    print(json.dumps({'kdamonds': [k.to_kvpairs(raw) for k in kdamonds]},
                     indent=4))

def main(args):
    _damon.ensure_root_permission()

    kdamonds, err = _damon_args.kdamonds_for(args)
    if err:
        print('invalid arguments (%s)' % err)
        exit(1)

    if args.format == 'json':
        pr_json(kdamonds, args.raw)

def set_argparser(parser):
    _damon_args.set_argparser(parser, add_record_options=False)
    parser.description = ' '.join([
        'format DAMON parameters'])
    parser.add_argument(
            '--format', choices=['json'], default='json',
            help='format of the output')
    parser.add_argument(
            '--raw', action='store_true',
            help='print numbers in machine friendly raw form')
