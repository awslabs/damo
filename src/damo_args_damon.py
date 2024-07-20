# SPDX-License-Identifier: GPL-2.0

import json

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

    if args.format == 'json':
        print(json.dumps({'kdamonds':
                          [k.to_kvpairs(args.raw) for k in kdamonds]},
                         indent=4))
    elif args.format == 'text':
        for idx, k in enumerate(kdamonds):
            print('kdamond %d' % idx)
            text = k.to_str(args.raw)
            for line in text.split('\n'):
                print('    %s' % line)

def set_argparser(parser):
    _damon_args.set_argparser(parser, add_record_options=False)
    parser.description = ' '.join([
        'format DAMON parameters'])
    parser.add_argument(
            '--format', choices=['json', 'text'], default='json',
            help='format of the output')
    parser.add_argument(
            '--raw', action='store_true',
            help='print numbers in machine friendly raw form')
