# SPDX-License-Identifier: GPL-2.0

import json

import _damon
import _damon_args
import _damon_sysfs

def main(args):
    _damon.ensure_root_and_initialized(args)

    feature_supports, err = _damon.get_feature_supports()
    if err != None:
        print('getting feature supports info failed (%s)' % err)
        exit(1)
    for feature in sorted(feature_supports.keys()):
        supported = feature_supports[feature]
        if args.type == 'all':
            print('%s: %s' % (feature,
                'Supported' if supported else 'Unsupported'))
        elif args.type == 'supported' and supported:
            print(feature)
        elif args.type == 'unsupported' and not supported:
            print(feature)
    if args.type == 'json':
        print(json.dumps(feature_supports, indent=4, sort_keys=True))

    if args.infer_version:
        if _damon._damon_fs is not _damon_sysfs:
            print('Version inferrence is unavailable')
            exit(1)
        print('Seems the version of DAMON is %s' %
              _damon_sysfs.infer_damon_version())

def set_argparser(parser):
    parser.add_argument('type', nargs='?',
            choices=['supported', 'unsupported', 'all', 'json'], default='all',
            help='type of features to listed')
    parser.add_argument('--infer_version', action='store_true',
                        help='infer version of DAMON')
    _damon_args.set_common_argparser(parser)
