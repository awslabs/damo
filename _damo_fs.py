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
def write_files(root, contents, dry):
    if isinstance(contents, list):
        for c in contents:
            err = write_files(root, c, dry)
            if err != None:
                return err
        return None

    if not isinstance(contents, dict):
        return ('write_files() received none-list, none-dict content: %s' %
                contents)

    for filename in contents:
        filepath = os.path.join(root, filename)
        if os.path.isfile(filepath):
            content = contents[filename]
            if dry:
                print('write \'%s\' to \'%s\'' % (content, filepath))
                continue
            try:
                with open(filepath, 'w') as f:
                    f.write(contents[filename])
            except Exception as e:
                return 'writing %s to %s failed (%s)' % (contents[filename],
                    filepath, e)
        elif os.path.isdir(filepath):
            return write_files(filepath, contents[filename], dry)
        else:
            return 'filepath (%s) is neither dir nor file' % (filepath)
    return None
