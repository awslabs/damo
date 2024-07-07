# SPDX-License-Identifier: GPL-2.0

import json

import _damon
import damo_reclaim
import damo_lru_sort

def main(args):
    _damon.ensure_root_permission()

    report = {}
    for damon_interface in ['sysfs', 'debugfs']:
        if not damon_interface in report:
            report[damon_interface] = {}

        err = _damon.set_damon_interface(damon_interface)
        if err is not None:
            print('DAMON interface set with %s failed: %s' %
                  (damon_interface, err))
            exit(1)
        feature_supports, err = _damon.get_feature_supports()
        if err is not None:
            print('get_feature_supports for %s failed: %s' %
                  (damon_interface, err))
            exit(1)
        report[damon_interface]['feature_supports'] = feature_supports

        report[damon_interface]['kdamonds'] = [
                k.to_kvpairs() for k in _damon.current_kdamonds()]

    report['damon_reclaim_status'] = damo_reclaim.darc_status()

    report['damon_lru_sort_status'] = damo_lru_sort.plrus_status()

    if args.verbose is True:
        print(json.dumps(report, indent=4))

def set_argparser(parser):
    parser.add_argument('--verbose', action='store_true',
                        help='make the output verbose')
