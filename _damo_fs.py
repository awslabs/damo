# SPDX-License-Identifier: GPL-2.0

import os

import _damon

'''Returns content and error'''
def read_file(filepath):
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except Exception as e:
        return None, 'reading %s failed (%s)' % (filepath, e)
    if _damon.pr_debug_log:
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
    if _damon.pr_debug_log:
        print('write \'%s\' to \'%s\'' % (content.strip(), filepath))
    try:
        with open(filepath, 'w') as f:
            f.write(content)
    except Exception as e:
        return 'writing %s to %s failed (%s)' % (content.strip(), filepath, e)
    return None

'''
operations can be either {path: content}, or [operations].  In the former case,
this function writes content to path, for all path/content pairs in the
dictionary.  In the latter case, operations in the list is executed
sequentially.  If the path is for a file, content should be a string.  If the
path is for a directory, the content should be yet another operations.  In the
latter case, upper-level path is prefixed to paths of the lower-level
operations paths.

For example:
    {
        'foo': 'bar',
        'dirA': {
            'fileA': '123',
            'fileB': '456',
            },
        [
            {'fileA': '42'},
            {'fileB': '4242'},
        ]
    }

    writes 'bar' to 'foo',
    writes '123' to 'dirA/fileA',
    writes '456' to 'dirA/fileB', and
    writes '42' to 'fileA' then writes '4242' to 'fileB',
    in any order

Return an error string if fails any write, or None otherwise.
'''
def write_files(operations, root=''):
    if not type(operations) in [list, dict]:
        return ('write_files() received none-list, none-dict content: %s' %
                operations)

    if isinstance(operations, list):
        for o in operations:
            err = write_files(o, root)
            if err != None:
                return err
        return None

    for filename in operations:
        filepath = os.path.join(root, filename)
        content = operations[filename]
        if os.path.isfile(filepath):
            err = write_file(filepath, content)
            if err != None:
                return err
        elif os.path.isdir(filepath):
            err = write_files(content, filepath)
            if err != None:
                return err
        else:
            return 'filepath (%s) is neither dir nor file' % (filepath)
    return None
