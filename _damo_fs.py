#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import os

def read_files(root, max_depth, current_depth, dry):
    contents = {}
    for filename in os.listdir(root):
        filepath = os.path.join(root, filename)
        if os.path.isdir(filepath):
            if max_depth != None and current_depth + 1 > max_depth:
                continue
            contents[filename] = read_files(filepath, max_depth,
                    current_depth + 1, dry)
        else:
            if dry:
                print('read \'%s\'' % filepath)
                continue
            try:
                with open(filepath, 'r') as f:
                    contents[filename] = f.read()
            except Exception as e:
                contents[filename] = 'read failed (%s)' % e
    return contents

'''Return error'''
def write_files(root, operations, dry):
    if isinstance(operations, list):
        for o in operations:
            err = write_files(root, o, dry)
            if err != None:
                return err
        return None

    if not isinstance(operations, dict):
        return ('write_files() received none-list, none-dict content: %s' %
                operations)

    for filename in operations:
        filepath = os.path.join(root, filename)
        if os.path.isfile(filepath):
            content = operations[filename]
            if dry:
                print('write \'%s\' to \'%s\'' % (content, filepath))
                continue
            try:
                with open(filepath, 'w') as f:
                    f.write(content)
            except Exception as e:
                return 'writing %s to %s failed (%s)' % (content, filepath, e)
        elif os.path.isdir(filepath):
            return write_files(filepath, content, dry)
        else:
            return 'filepath (%s) is neither dir nor file' % (filepath)
    return None
