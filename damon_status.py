#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import json

import _damon

def set_argparser(parser):
    parser.add_argument('target', choices=['schemes_stats', 'all',
        'damon_interface'],
            nargs='?', default='all', help='What status to show')
    _damon.set_common_argparser(parser)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    # Require root permission
    _damon.ensure_root_permission()

    err = _damon.initialize(args, skip_dirs_population=True)
    if err != None:
        print(err)
        exit(1)

    content = _damon.read_damon_fs()
    if args.target == 'all':
        print(json.dumps(content, indent=4, sort_keys=True))
    elif args.target == 'schemes_stats':
        print('# <kdamond> <context> <scheme> <field> <value>')
        kdamonds = content['kdamonds']
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
    elif args.target == 'damon_interface':
        print(_damon.damon_interface())

if __name__ == '__main__':
    main()
