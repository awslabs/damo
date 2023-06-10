# SPDX-License-Identifier: GPL-2.0

"""
Show status of DAMON.
"""

import damo_stat_schemes

import _damo_fmt_str
import _damon
import _damon_args

def update_pr_kdamonds_summary(json_format, raw_nr):
    kdamonds = _damon.current_kdamonds()
    summary = [k.summary_str() for k in kdamonds]
    if json_format:
        print(json.dumps(summary, indent=4))
        return
    print('\n'.join(summary))

def update_pr_kdamonds(json_format, raw_nr):
    kdamonds, err = _damon.update_read_kdamonds()
    if err:
        print(err)
        return
    if json_format:
        print(json.dumps([k.to_kvpairs(raw_nr) for k in kdamonds], indent=4))
    else:
        for idx, k in enumerate(kdamonds):
            print('kdamond %d' % idx)
            print(_damo_fmt_str.indent_lines( k.to_str(raw_nr), 4))


def set_argparser(parser):
    parser.add_argument('target', choices=['kdamonds', 'schemes_stats'],
            help='what status to show')
    parser.add_argument('--detail', action='store_true', default=False,
            help='show detailed status')
    parser.add_argument('--json', action='store_true', default=False,
            help='print output in json format')
    parser.add_argument('--raw', action='store_true', default=False,
            help='print raw numbers')
    _damon_args.set_common_argparser(parser)
    return parser

def main(args=None):
    if not args:
        parser = set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    if args.target == 'kdamonds':
        if not args.detail:
            update_pr_kdamonds_summary(args.json, args.raw)
        else:
            update_pr_kdamonds(args.json, args.raw)
    elif args.target == 'schemes_stats':
        damo_stat_schemes.update_pr_schemes_stats(args.raw)

if __name__ == '__main__':
    main()
