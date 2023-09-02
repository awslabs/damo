# SPDX-License-Identifier: GPL-2.0

"""
Apply given operation schemes.
"""

import os
import signal

import _damon
import _damon_args

cleaning = False
def cleanup_exit(exit_code):
    global cleaning
    if cleaning == True:
        return
    cleaning = True
    # ignore returning error, as kdamonds may already finished
    _damon.turn_damon_off(kdamonds_idxs)
    err = _damon.stage_kdamonds(orig_kdamonds)
    if err:
        print('failed restoring previous kdamonds setup (%s)' % err)
    exit(exit_code)

def sighandler(signum, frame):
    print('\nsignal %s received' % signum)
    cleanup_exit(signum)

def set_argparser(parser):
    return _damon_args.set_argparser(parser, add_record_options=False)

def main(args=None):
    global orig_kdamonds
    global kdamonds_idxs

    if not args:
        parser = set_argparser(None)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    orig_kdamonds = _damon.current_kdamonds()
    kdamonds_idxs = []

    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    err, kdamonds = _damon_args.turn_damon_on(args)
    if err:
        print('could not turn DAMON on (%s)' % err)
        cleanup_exit(-3)

    kdamonds_idxs = ['%d' % idx for idx, k in enumerate(kdamonds)]

    print('Press Ctrl+C to stop')
    if _damon_args.self_started_target(args):
        os.waitpid(kdamonds[0].contexts[0].targets[0].pid, 0)
    # damon will turn it off by itself if the target tasks are terminated.
    _damon.wait_kdamonds_turned_off()

    cleanup_exit(0)

if __name__ == '__main__':
    main()
