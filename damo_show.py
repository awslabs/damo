# SPDX-License-Identifier: GPL-2.0

"""
Show status and results of DAMON.
"""

import _damon
import _damon_args

def set_argparser(parser):
    return _damon_args.set_common_argparser(parser)

def main(args=None):
    if not args:
        parser = set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)
    print('to be implemented')

if __name__ == '__main__':
    main()
