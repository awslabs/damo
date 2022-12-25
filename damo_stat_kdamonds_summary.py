#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse

import _damon

def update_pr_damo_stat():
    kdamonds = _damon.current_kdamonds()
    print('\n'.join([k.summary_str() for k in kdamonds]))

def set_argparser(parser):
    parser.add_argument('--delay', metavar='<secs>', default=3, type=float,
            help='delay between repeated status prints')
    parser.add_argument('--count', metavar='<count>', default=1, type=int,
            help='number of repeated status prints')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    # Require root permission
    _damon.ensure_root_permission()
    _damon.ensure_initialized(args)

    for i in range(args.count):
        update_pr_damo_stat()
        if i != args.count - 1:
            time.sleep(args.delay)

if __name__ == '__main__':
    main()
