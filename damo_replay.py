# SPDX-License-Identifier: GPL-2.0

def main(args):
    print('under construction')

def set_argparser(parser):
    parser.add_argument('--input', metavar='<file>', default='damon.data',
                        help='record file to replay')
    parser.description = 'Replay monitored access pattern'
    return parser
