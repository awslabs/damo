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

import _damon
import _damon_args

'''
kdamonds uses collections.OrderedDict.  yaml.dump() adds
constructor comments for those like below.

    kdamonds:
    - !!python/object/apply:collections.OrderedDict
      - - - state
          - null
        - - pid
          - null

yaml.safe_load(), which is used from _damon_args to read the yaml output again,
fails at parsing it.  To support it, we should use yaml.load() with a specific
loader.

However, we use OrderedDict to make json or yaml-like dumped output keeps the
order.  That's for letting it easy to read by human beings.  Here, the added
constructor comment and slightly changed format are for machines.  Also
from_kvpairs() methods for DAMON parameters don't really care about the orders
and the type.

So, adding the handling on dumping part instead of the loading part would make
the result simpler while it all works seamlessly.  Use a custom dumper that
prints OrderedDict as normal dict.
'''
def pr_kdamonds_yaml(kdamonds, raw):
    def ordered_dict_representer(dumper, ordered_dict):
        # represnet collections.OrderedDict object as normal dict, but while
        # keeping the dumped order; the order will be ignored when loaded
        # again, but that's not a problem for Kdamonds.
        return dumper.represent_dict(ordered_dict.items())

    class OrderedDumper(yaml.SafeDumper):
        # Same to safe dumper but represent OrderedDict using
        # ordered_dict_representer
        pass

    OrderedDumper.add_representer(
            collections.OrderedDict, ordered_dict_representer)

    print(yaml.dump(
        {'kdamonds': [k.to_kvpairs(raw) for k in kdamonds]},
        Dumper=OrderedDumper, default_flow_style=False, sort_keys=False))

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
        pr_kdamonds_yaml(kdamonds, args.raw)

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
