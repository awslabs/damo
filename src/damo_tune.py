# SPDX-License-Identifier: GPL-2.0

"""
Update DAMON input parameters.
"""

import _damon
import _damon_args

def main(args):
    _damon.ensure_root_and_initialized(args)

    if not _damon.any_kdamond_running():
        print('DAMON is not turned on')
        exit(1)

    kdamonds, err = _damon_args.commit_kdamonds(args, args.quota_goals_only)
    if err:
        print('tuning failed (%s)' % err)
        exit(1)

def set_argparser(parser):
    parser.description = 'Update DAMON parameters'
    parser.add_argument('--quota_goals_only', action='store_true',
            help='commit quota goals change only')
    _damon_args.set_argparser(parser, add_record_options=False, min_help=True)
