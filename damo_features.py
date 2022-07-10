#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import _damon

def set_argparser(parser):
    parser.add_argument('type', choices=['supported', 'unsupported', 'all'],
            default='all', nargs='?',
            help='type of features to listed')
    _damon.set_common_argparser(parser)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.initialize(args)

    for feature in sorted(_damon.features):
        supported = _damon.feature_supported(feature)
        if args.type == 'all':
            print('%s: %s' % (feature,
                'Supported' if supported else 'Unsupported'))
        elif args.type == 'supported' and supported:
            print(feature)
        elif args.type == 'unsupported' and not supported:
            print(feature)

if __name__ == '__main__':
    main()
