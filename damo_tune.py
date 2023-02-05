#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Update DAMON input parameters.
"""

import _damon
import _damon_args

def set_argparser(parser):
    return _damon_args.set_argparser(parser, add_record_options=False)

def main(args=None):
    if not args:
        parser = set_argparser(None)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    if _damon.damon_interface() == 'debugfs':
        print('tune does not support debugfs interface')
        exit(1)

    if _damon.every_kdamond_turned_off():
        print('DAMON is not turned on')
        exit(1)

    kdamonds, err = _damon_args.apply_kdamonds(args)
    if err:
        print('could not apply inputs (%s)' % err)
    err = _damon.commit_inputs(kdamonds)
    if err:
        print('could not commit inputs (%s)' % err)

if __name__ == '__main__':
    main()
