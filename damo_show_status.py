# SPDX-License-Identifier: GPL-2.0

"""
Show status of DAMON.
"""

import _damon
import _damon_args

import damo_stat_kdamonds

def set_argparser(parser):
    parser.add_argument('target', metavar='<target>', choices=['kdamonds'],
            help='what status to show')
    _damon_args.set_common_argparser(parser)
    return parser

def main(args=None):
    if not args:
        parser = set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    if args.target == 'kdamonds':
        damo_stat_kdamonds.update_pr_kdamonds_summary(False, False)

if __name__ == '__main__':
    main()
