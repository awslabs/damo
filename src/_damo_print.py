# SPDX-License-Identifier: GPL-2.0

import os
import subprocess
import tempfile

def pr_with_pager_if_needed(text):
    try:
        nr_terminal_lines = os.get_terminal_size().lines
    except:
        nr_terminal_lines = 50
    if text.count('\n') <= nr_terminal_lines:
        print(text)
        return

    fd, tmp_path = tempfile.mkstemp(prefix='damo_show-')
    with open(tmp_path, 'w') as f:
        f.write(text)
    subprocess.call(['less', '--RAW-CONTROL-CHARS', '--no-init', tmp_path])
    os.remove(tmp_path)
