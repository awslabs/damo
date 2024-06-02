# SPDX-License-Identifier: GPL-2.0

class DamoSubCmdModule:
    set_argparser = lambda self, args: args
    main = lambda self, args: args

    def __init__(self, set_argparser, main):
        if set_argparser != None:
            self.set_argparser = set_argparser
        if main != None:
            self.main = main

class DamoSubCmd:
    name = None
    msg = None
    module = None

    def __init__(self, name, module, msg):
        self.name = name
        self.module = module
        self.msg = msg

    def add_parser(self, subparsers):
        subparser = subparsers.add_parser(self.name, help=self.msg)
        subparser.description = self.msg
        self.module.set_argparser(subparser)

    def execute(self, args):
        self.module.main(args)
