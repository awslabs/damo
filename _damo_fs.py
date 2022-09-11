#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import os

import _damon

def __read_files(root, max_depth, current_depth):
    contents = {}
    for filename in os.listdir(root):
        filepath = os.path.join(root, filename)
        if os.path.isdir(filepath):
            if max_depth != None and current_depth + 1 > max_depth:
                continue
            contents[filename] = __read_files(filepath, max_depth,
                    current_depth + 1)
        else:
            try:
                with open(filepath, 'r') as f:
                    contents[filename] = f.read()
            except Exception as e:
                contents[filename] = 'read failed (%s)' % e
    return contents

def read_files_recursive(root):
    return __read_files(root, None, 1)

def __write_files(root, operations):
    if isinstance(operations, list):
        for o in operations:
            err = __write_files(root, o)
            if err != None:
                return err
        return None

    if not isinstance(operations, dict):
        return ('__write_files() received none-list, none-dict content: %s' %
                operations)

    for filename in operations:
        filepath = os.path.join(root, filename)
        content = operations[filename]
        if os.path.isfile(filepath):
            try:
                with open(filepath, 'w') as f:
                    if _damon.pr_debug_log:
                        print('write \'%s\' to \'%s\'' % (content, filepath))
                    f.write(content)
            except Exception as e:
                return 'writing %s to %s failed (%s)' % (content, filepath, e)
        elif os.path.isdir(filepath):
            err = __write_files(filepath, content)
            if err != None:
                return err
        else:
            return 'filepath (%s) is neither dir nor file' % (filepath)
    return None

'''
operations can be either {path: content}, or [operations].  In the former case,
this function writes content to path, for all path/content pairs in the
dictionary.  In the latter case, operations in the list is executed
sequentially.  If the path is for a file, content should be a string.  If the
path is for a directory, the content should be yet another operations.  In the
latter case, upper-level path is prefixed to paths of the lower-level
operations paths.

Return an error string if fails any write, or None otherwise.
'''
def write_files(operations):
    return __write_files('', operations)
