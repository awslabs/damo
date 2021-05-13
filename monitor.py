#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"Record and report data access pattern in realtime"

import argparse
import os
import signal
import subprocess
import sys
import time

import record
import heats
import wss

def cleanup():
    if target_is_cmd and cmd_pipe.poll() != None:
        cmd_pipe.kill()


def sighandler(signum, frame):
    print('\nsignal %s received' % signum)
    cleanup()

def set_argparser(parser):
    parser.add_argument('target', type=str, metavar='<target>',
            help='monitoring target (command, pid or \'paddr\')')
    parser.add_argument('--report_type', type=str, metavar='<report type>',
            choices=['heats', 'wss'], default='heats',
            help='report type')
    parser.add_argument('--delay', type=float, metavar='<seconds>', default=3,
            help='deplay between updates in seconds.')
    parser.add_argument('--count', type=int, metavar='<count>', default=0,
            help='number of updates.')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    global target_is_cmd
    global cmd_pipe

    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    target_is_cmd = False
    target = args.target
    target_fields = target.split()
    if target == 'paddr':
        pass
    elif not subprocess.call('which %s &> /dev/null' % target_fields[0],
            shell=True, executable='/bin/bash'):
        target_is_cmd = True
        cmd_pipe = subprocess.Popen(target, shell=True, executable='/bin/bash',
                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        target = cmd_pipe.pid
    else:
        try:
            pid = int(target)
        except:
            print('invalid target \'%s\'' % target)
            exit(1)

    bindir = os.path.dirname(sys.argv[0])
    damo = os.path.join(bindir, 'damo')

    record_cmd = '%s record \"%s\" --timeout %s' % (damo, target,
            args.delay)

    if args.report_type == 'heats':
        report_cmd = '%s report heats --heatmap stdout --resol 10 80' % damo
    else:
        report_cmd = '%s report wss' % damo


    nr_reports = 0
    while not args.count or nr_reports < args.count:
        if target_is_cmd and cmd_pipe.poll() != None:
            break
        try:
            subprocess.check_output(record_cmd, shell=True,
                    stderr=subprocess.STDOUT, executable='/bin/bash')
            output = subprocess.check_output(report_cmd, shell=True,
                    executable='/bin/bash').decode()
            if args.report_type == 'heats':
                for line in output.strip().split('\n'):
                    if not line.startswith('#'):
                        print(line)
            else:
                print(output)
        except subprocess.CalledProcessError as e:
            break
        nr_reports += 1

    cleanup()

if __name__ == '__main__':
    main()
