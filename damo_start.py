#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Start DAMON with given parameters.
"""

import _damon
import _damon_args

def set_argparser(parser):
    return _damon_args.set_argparser(parser, add_record_options=False)

def main(args=None):
    if not args:
        parser = set_pargparser(None)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    err, kdamonds = _damon_args.turn_damon_on(args)
    if err:
        print('could not turn on damon (%s)' % err)
        exit(1)

if __name__ == '__main__':
    main()
