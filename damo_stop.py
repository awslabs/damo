# SPDX-License-Identifier: GPL-2.0

"""
Stop DAMON.
"""

import _damon
import _damon_args

def set_argparser(parser):
    _damon_args.set_common_argparser(parser)
    parser.description = 'Stop DAMON'
    return parser

def main(args=None):
    if not args:
        parser = set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    running_kdamond_idxs = _damon.running_kdamond_idxs()
    if len(running_kdamond_idxs) == 0:
        print('DAMON is not turned on')
        exit(1)

    err = _damon.turn_damon_off(running_kdamond_idxs)
    if err:
        print('DAMON turn off failed (%s)' % err)
        exit(1)

if __name__ == '__main__':
    main()
