#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import json

import _damon

def set_argparser(parser):
    parser.add_argument('target', choices=['schemes_stats',
        'schemes_tried_regions', 'all', 'damon_interface'],
            nargs='?', default='all', help='What status to show')
    _damon.set_common_argparser(parser)

def pr_schemes_stats(damon_fs_content):
    print('# <kdamond> <context> <scheme> <field> <value>')
    kdamonds = damon_fs_content['kdamonds']
    nr_kdamonds = int(kdamonds['nr_kdamonds'])
    if nr_kdamonds == 0:
        print('no kdamond exist')
    for i in range(nr_kdamonds):
        contexts = kdamonds['%d' % i]['contexts']
        nr_contexts = int(contexts['nr_contexts'])
        if nr_contexts == 0:
            print('kdamond %d has no context' % i)
            continue
        for c in range(nr_contexts):
            schemes = contexts['%d' % c]['schemes']
            nr_schemes = int(schemes['nr_schemes'])
            if nr_schemes == 0:
                print('kdamond %d context %d has no scheme' % (i, c))
                continue
            for s in range(nr_schemes):
                stats = schemes['%d' % s]['stats']
                for f in ['nr_tried', 'sz_tried',
                        'nr_applied', 'sz_applied', 'qt_exceeds']:
                    print('%d %d %d %s: %d' % (i, c, s, f, int(stats[f])))

def pr_schemes_tried_regions(damon_fs_content):
    kdamonds = damon_fs_content['kdamonds']
    nr_kdamonds = int(kdamonds['nr_kdamonds'])
    if nr_kdamonds == 0:
        print('no kdamond exist')
    for i in range(nr_kdamonds):
        contexts = kdamonds['%d' % i]['contexts']
        nr_contexts = int(contexts['nr_contexts'])
        if nr_contexts == 0:
            print('kdamond %d has no context' % i)
            continue
        for c in range(nr_contexts):
            schemes = contexts['%d' % c]['schemes']
            nr_schemes = int(schemes['nr_schemes'])
            if nr_schemes == 0:
                print('kdamond %d context %d has no scheme' % (i, c))
                continue
            for s in range(nr_schemes):
                tried_regions = schemes['%d' % s]['tried_regions']
                nr_tried_regions = len(tried_regions)
                for r in range(nr_tried_regions):
                    region = tried_regions['%d' % r]
                    start = int(region['start'])
                    end = int(region['end'])

                    print('%d-%d (%d): nr_accesses %d, age %d' % (
                        start, end, end - start,
                        int(region['nr_accesses']), int(region['age'])))

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    # Require root permission
    _damon.ensure_root_permission()
    _damon.ensure_initialized(args, True)

    if _damon.is_damon_running():
        _damon.write_damon_fs({'kdamonds/0/state': 'update_schemes_stats'})
        _damon.write_damon_fs({'kdamonds/0/state':
            'update_schemes_tried_regions'})
    content = _damon.read_damon_fs()
    if args.target == 'all':
        print(json.dumps(content, indent=4, sort_keys=True))
    elif args.target == 'schemes_stats':
        pr_schemes_stats(content)
    elif args.target == 'schemes_tried_regions':
        pr_schemes_tried_regions(content)
    elif args.target == 'damon_interface':
        print(_damon.damon_interface())

if __name__ == '__main__':
    main()
