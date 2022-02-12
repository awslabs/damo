#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON sysfs control.
"""

import _damon

feature_supports = None

def _write(content, filepath):
    with open(filepath, 'w') as f:
        f.write(content)

def _ensure_sysfs_dir_for_damo():
    if not os.isdir(sysfs_damon + 'kdamonds/0')):
        _write('1', sysfs_damon + 'kdamonds/nr')
    if not os.isdir(sysfs_damon + 'kdamonds/0/contexts/0'):
        _write('1', sysfs_damon + 'kdamonds/0/contexts/nr')

def set_target(tid, init_regions):
    _ensure_sysfs_dir_for_damo()
    if not os.isdir(sysfs_damon + 'kdamonds/0/contexts/0/targets/0'):
        _write('1', sysfs_damon + 'kdamonds/0/contexts/0/targets/nr')
    if tid == 'paddr':
        _write('paddr\n', sysfs_damon + 'kdamonds/0/contexts/0/damon_type')
    else:
        _write('%s\n' % tid, sysfs_damon +
                'kdamonds/0/contexts/0/targets/0/pid')

    _write('%s' % len(init_regions), sysfs_damon +
            'kdamonds/0/contexts/0/targets/0/regions/nr')
    for idx, region in enumerate(init_regions):
        _write(region[0], sysfs_damon +
                'kdamonds/0/contexts/0/targets/0/regions/%d/start')
        _write(region[1], sysfs_damon +
                'kdamonds/0/contexts/0/targets/0/regions/%d/end')

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

def chk_update():
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
