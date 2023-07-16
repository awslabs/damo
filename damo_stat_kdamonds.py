# SPDX-License-Identifier: GPL-2.0

import argparse
import json

import _damo_fmt_str
import _damon
import damo_stat
import damo_status

def set_argparser(parser):
    damo_stat.set_common_argparser(parser)
    parser.add_argument('--detail', action='store_true',
            help='print detailed stat of kdamonds')
    parser.add_argument('--json', action='store_true',
            help='print kdamond in json format')

def __main(args):
    if not args.detail:
        damo_status.update_pr_kdamonds_summary(args.json, args.raw)
    else:
        damo_status.update_pr_kdamonds(args.json, args.raw)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    damo_stat.run_count_delay(__main, args)

if __name__ == '__main__':
    main()
