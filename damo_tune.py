# SPDX-License-Identifier: GPL-2.0

"""
Update DAMON input parameters.
"""

import _damon
import _damon_args

def evaluate_args_for_quota_goals(args):
    if args.damos_action:
        return True, None
    
    for key, value in args.__dict__.items():
        if key.startswith('damos_') and len(value):
            if key == 'damos_action': continue
            return False, 'no \'damos_action\' provided in arguments while using --damos_* option(s)'

    return True, None

def main(args):
    _damon.ensure_root_and_initialized(args)

    if not _damon.any_kdamond_running():
        print('DAMON is not turned on')
        exit(1)

    correct_args, err = evaluate_args_for_quota_goals(args)

    if (correct_args is not True and err is not None):
        print('Tune error: incorrect arguments: %s' % err)
        exit(1)

    kdamonds, err = _damon_args.commit_kdamonds(args, args.quota_goals_only)
    if err:
        print('tuning failed (%s)' % err)
        exit(1)

def set_argparser(parser):
    parser.description = 'Update DAMON parameters'
    parser.add_argument('--quota_goals_only', action='store_true',
            help='commit quota goals change only')
    return _damon_args.set_argparser(parser, add_record_options=False)
