# SPDX-License-Identifier: GPL-2.0

import argparse

import damo_status
import damo_stat

import _damo_deprecation_notice
import _damo_fmt_str
import _damo_subcmds
import _damon

def set_argparser(parser):
    damo_stat.set_common_argparser(parser)

def __main(args):
    if args.stat_type == 'schemes_stats':
        damo_status.update_pr_schemes_stats(args.raw)
    elif args.stat_type == 'schemes_tried_regions':
        damo_status.update_pr_schemes_tried_regions(args.raw)

def main(args=None):
    _damo_deprecation_notice.will_be_deprecated('\'damo stat schemes*\'',
            'near future', 'Use \'damo show status schemes*\' instead')
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    damo_stat.run_count_delay(__main, args)

    for i in range(args.count):
        if i != args.count - 1:
            time.sleep(args.delay)

if __name__ == '__main__':
    main()
