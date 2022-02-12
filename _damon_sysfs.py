#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON sysfs control.
"""

import _damon

feature_supports = None

def set_target(tid, init_regions):
    if tid != 'paddr':
        set_target_pid(tid)

    pass

def turn_damon(on_off):
    pass

def is_damon_running():
    pass

def attrs_apply(attrs):
    pass

def current_attrs():
    pass

def feature_supported(feature):
    if feature_supports == None:
        chk_update()
    return feature_supports[feature]

def get_supported_features():
    if feature_supports == None:
        chk_update()
    return feature_supports

def chk_update(sysfs_damon='/sys/kernel/mm/damon/admin/'):
    if not os.path.isdir(sysfs_damon):
        print('damon sysfs dir (%s) not found' % sysfs_damon)
        exit(1)

    feature_supports = {x: True for x in _damon.features}

def cmd_args_to_attrs(args):
    pass

def cmd_args_to_init_regions(args):
    pass

def set_attrs_argparser(parser):
    pass

def set_init_regions_argparser(parser):
    pass
