# SPDX-License-Identifier: GPL-2.0

"Record and report data access pattern in realtime"

import os
import signal
import subprocess
import sys

import _damon
import _damon_args

def cleanup():
    if target_type == _damon_args.target_type_cmd and cmd_pipe.poll() == None:
        cmd_pipe.kill()

def sighandler(signum, frame):
    print('\nsignal %s received' % signum)
    cleanup()

def main(args):
    _damon.ensure_root_permission()

    global target_type
    global cmd_pipe

    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    target = args.target
    target_fields = target.split()
    target_type = _damon_args.deduced_target_type(target)
    if target_type == None:
        print('invalid target \'%s\'' % target)
        exit(1)
    if target_type == _damon_args.target_type_explicit and target == 'paddr':
        pass
    elif target_type == _damon_args.target_type_cmd:
        cmd_pipe = subprocess.Popen(target, shell=True, executable='/bin/bash',
                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        target = cmd_pipe.pid
    else:
        pid = int(target)

    bindir = os.path.dirname(sys.argv[0])
    damo = os.path.join(bindir, 'damo')

    record_cmd = 'timeout %s %s record \"%s\"' % (args.delay, damo, target)

    report_cmd = [damo]
    if args.report_type == 'heats':
        report_cmd += 'report heats --heatmap stdout --resol 10 80'.split()
    else:
        report_cmd += ['report', args.report_type]

    nr_reports = 0
    while not args.count or nr_reports < args.count:
        if (target_type == _damon_args.target_type_cmd and
                cmd_pipe.poll() != None):
            break
        try:
            subprocess.check_output(record_cmd, shell=True,
                    stderr=subprocess.STDOUT, executable='/bin/bash')
        except subprocess.CalledProcessError as e:
            pass
        try:
            output = subprocess.check_output(report_cmd).decode()
            if args.report_type == 'heats':
                for line in output.strip().split('\n'):
                    if not line.startswith('#'):
                        print(line)
            else:
                print(output)
        except subprocess.CalledProcessError as e:
            pass
        nr_reports += 1

    cleanup()

def set_argparser(parser):
    parser.add_argument('target', type=str, metavar='<target>',
            help='monitoring target (command, pid or \'paddr\')')
    parser.add_argument(
            '--report_type', type=str, choices=['heats', 'wss', 'holistic'],
            default='heats', help='report type')
    parser.add_argument('--delay', type=float, metavar='<seconds>', default=3,
            help='deplay between updates in seconds.')
    parser.add_argument('--count', type=int, metavar='<count>', default=0,
            help='number of updates.')
