# SPDX-License-Identifier: GPL-2.0

"""
Update DAMON input parameters.
"""

import _damon
import _damon_args

def evaluate_args_for_tune(args):
    '''
    Verify if 'damons_action' is present when any 'damos_*' is specified
    '''
    if not args.damos_action:
        for key, value in args.__dict__.items():
            if key.startswith('damos_') and len(value):
                if key == 'damos_action': continue
                return False, '\'damos_action\' not specified while using --damos_* option(s)'

    '''
    Verify if 'reset_interval_ms' is specified in args when setting quota goals
    '''
    if args.damos_quota_goal:
        damos_quotas = args.damos_quotas

        if not len(damos_quotas):
            return False, '\'reset_interval_ms\' not specified when setting quota goals'

        #reset_interval_ms is specified in --damos_quotas as 3rd arg
        for quota in damos_quotas:
            if len(quota) < 3:
                return False, '\'reset_interval_ms\' not specified when setting quota goals'
    
    return True, None

def main(args):
    _damon.ensure_root_and_initialized(args)

    if not _damon.any_kdamond_running():
        print('DAMON is not turned on')
        exit(1)

    correct_args, err = evaluate_args_for_tune(args)

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
