# SPDX-License-Identifier: GPL-2.0

import json
import sys

try:
    import yaml
except ModuleNotFoundError as e:
    # do nothing.  The yaml using functions should handle the exception
    # properly.
    pass

import _damon
import _damon_args

def main(args):
    if args.format == 'yaml':
        if not 'yaml' in sys.modules:
            print('yaml module import failed')
            exit(1)
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
    elif args.format == 'yaml':
        print(yaml.dump({'kdamonds':
                          [k.to_kvpairs(args.raw) for k in kdamonds]}))

def set_argparser(parser):
    _damon_args.set_argparser(parser, add_record_options=False)
    parser.description = ' '.join([
        'format DAMON parameters'])
    parser.add_argument(
            '--format', choices=['json', 'yaml'], default='json',
            help='format of the output')
    parser.add_argument(
            '--raw', action='store_true',
            help='print numbers in machine friendly raw form')
