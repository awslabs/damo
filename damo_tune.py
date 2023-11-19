# SPDX-License-Identifier: GPL-2.0

"""
Update DAMON input parameters.
"""

import _damon
import _damon_args

def set_argparser(parser):
    parser.description = 'Update DAMON parameters'
    parser.add_argument('--quota_goals_only', action='store_true',
            help='commit quota goals change only')
    return _damon_args.set_argparser(parser, add_record_options=False)

def main(args=None):
    if not args:
        parser = set_argparser(None)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    if not _damon.any_kdamond_running():
        print('DAMON is not turned on')
        exit(1)

    kdamonds, err = _damon_args.commit_kdamonds(args, args.quota_goals_only)
    if err:
        print('tuning failed (%s)' % err)
        exit(1)

if __name__ == '__main__':
    main()
