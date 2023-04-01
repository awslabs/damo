#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import json

import damo_stat

import _damo_fmt_str
import _damon

def update_pr_kdamonds_summary(json_format, raw_nr):
    kdamonds = _damon.current_kdamonds()
    summary = [k.summary_str() for k in kdamonds]
    if json_format:
        print(json.dumps(summary, indent=4))
        return
    print('\n'.join(summary))

def update_pr_kdamonds(json_format, raw_nr):
    err = _damon.update_schemes_stats()
    if err:
        print(err)
        return
    kdamonds = _damon.current_kdamonds()
    if json_format:
        print(json.dumps([k.to_kvpairs(raw_nr) for k in kdamonds], indent=4))
    else:
        print('kdamonds')
        print(_damo_fmt_str.indent_lines(
            '\n\n'.join([k.to_str(raw_nr) for k in kdamonds]), 4))

def set_argparser(parser):
    damo_stat.set_common_argparser(parser)
    parser.add_argument('--detail', action='store_true',
            help='print detailed stat of kdamonds')
    parser.add_argument('--json', action='store_true',
            help='print kdamond in json format')

def __main(args):
    if not args.detail:
        update_pr_kdamonds_summary(args.json, args.raw)
    else:
        update_pr_kdamonds(args.json, args.raw)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    damo_stat.run_count_delay(__main, args)

if __name__ == '__main__':
    main()
