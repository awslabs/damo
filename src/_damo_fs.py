# SPDX-License-Identifier: GPL-2.0

import os

debug_do_print = False
debug_dryrun_logs = None
debug_dryrun_read_outputs = None

def debug_print_ops(do_print):
    global debug_do_print
    debug_do_print = do_print

def debug_dryrun(read_outputs):
    '''Set damo_fs to not do the real io, but just log the ops in a buffer'''
    global debug_dryrun_logs
    global debug_dryrun_read_outputs
    debug_dryrun_logs = []
    debug_dryrun_read_outputs = read_outputs

def debug_get_dryrun_logs():
    return debug_dryrun_logs

'''Returns content and error'''
def read_file(filepath):
    if debug_dryrun_logs is not None:
        content = debug_dryrun_read_outputs[filepath]
        debug_dryrun_logs.append('read \'%s\': \'%s\'' %
                                 (filepath, content.strip()))
    else:
        try:
            with open(filepath, 'r') as f:
                content = f.read()
        except Exception as e:
            return None, 'reading %s failed (%s)' % (filepath, e)
    if debug_do_print:
        print('read \'%s\': \'%s\'' % (filepath, content.strip()))
    return content, None

def read_files(root):
    contents = {}
    for filename in os.listdir(root):
        filepath = os.path.join(root, filename)
        if os.path.isdir(filepath):
            contents[filename] = read_files(filepath)
        else:
            contents[filename], err = read_file(filepath)
            if err != None:
                contents[filename] = 'read failed (%s)' % err
    return contents

'''
Returns None if success error string otherwise
'''
def write_file(filepath, content):
    if debug_do_print:
        print('write \'%s\' to \'%s\'' % (content.strip(), filepath))
    if debug_dryrun_logs is not None:
        debug_dryrun_logs.append(
                'write \'%s\' to \'%s\'' % (content.strip(), filepath))
        return None
    try:
        with open(filepath, 'w') as f:
            f.write(content)
    except Exception as e:
        return 'writing %s to %s failed (%s)' % (content.strip(), filepath, e)
    return None

def dev_mount_point(dev):
    '''Returns mount point of specific device.  None if not mounted'''
    with open('/proc/mounts', 'r') as f:
        for line in f:
            dev_name, mount_point, dev_fs = line.split()[:3]
            if dev_fs == dev:
                return mount_point
    return None
