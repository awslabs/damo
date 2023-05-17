# SPDX-License-Identifier: GPL-2.0

import json

import _damon
import _damon_args

def set_argparser(parser):
    parser.add_argument('type', nargs='?',
            choices=['supported', 'unsupported', 'all', 'json'], default='all',
            help='type of features to listed')
    _damon_args.set_common_argparser(parser)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    feature_dir = {}
    for feature in sorted(_damon.features):
        supported = _damon.feature_supported(feature)
        if args.type == 'all':
            print('%s: %s' % (feature,
                'Supported' if supported else 'Unsupported'))
        elif args.type == 'supported' and supported:
            print(feature)
        elif args.type == 'unsupported' and not supported:
            print(feature)
        elif args.type == 'json':
            feature_dir[feature] = supported
    if args.type == 'json':
        print(json.dumps(feature_dir, indent=4, sort_keys=True))

if __name__ == '__main__':
    main()
