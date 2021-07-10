#!/usr/bin/env python3

import _damon

def set_argparser(parser):
    parser.add_argument('type', choices=['supported', 'unsupported', 'all'],
            default='all', nargs='?',
            help='type of features to listed')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    features = _damon.get_supported_features()

    for feature in sorted(features.keys()):
        if args.type == 'all':
            print('%s: %s' % (feature,
                'Supported' if features[feature] else 'Unsupported'))
        elif args.type == 'supported' and features[feature]:
            print(feature)
        elif args.type == 'unsupported' and not features[feature]:
            print(feature)

if __name__ == '__main__':
    main()
