# SPDX-License-Identifier: GPL-2.0

"""
Show status of DAMON.
"""

def set_argparser(parser):
    return parser

def main(args=None):
    if not args:
        parser = set_argparser(parser)
        args = parser.parse_args()

if __name__ == '__main__':
    main()
