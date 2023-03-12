#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import sys

if sys.version.startswith('2.'):
    sys.stderr.write('''
WARNING: damo will remove python2 support by 2023-Q2.  Please report your
    usecase to sj@kernel.org, damon@lists.linux.dev and linux-mm@kvack.org if
    you depend on those.

''')
