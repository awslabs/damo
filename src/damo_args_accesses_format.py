# SPDX-License-Identifier: GPL-2.0

import collections
import json

import _damo_yaml
import damo_report_access

def main(args):
    handled = damo_report_access.handle_ls_keywords(args)
    if handled:
        return
    fmt = damo_report_access.set_formats(args)
    kvpairs = fmt.to_kvpairs(raw=args.raw)

    if args.format == 'json':
        print(json.dumps(kvpairs, indent=4))
    elif args.format == 'yaml':
        text, err = _damo_yaml.dump(kvpairs)
        if err is not None:
            print('yaml dump failed (%s)' % err)
            exit(1)
        print(text)

def set_argparser(parser):
    parser.description = ' '.join([
        'format DAMON monitoring results visualization parameters'])
    damo_report_access.add_fmt_args(parser)
    parser.add_argument(
            '--format', choices=['json', 'yaml'], default='json',
            help='format of the output')
    parser.add_argument(
            '--raw', action='store_true',
            help='print numbers in machine friendly raw form')
