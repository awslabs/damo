# SPDX-License-Identifier: GPL-2.0

import os
import subprocess
import sys

import _damo_deprecation_notice

if sys.version.startswith('2.'):
    _damo_deprecation_notice.deprecated(feature='Python2 support of damo',
            deadline='2023-Q2')

# For supporting python 2.6
try:
    subprocess.DEVNULL = subprocess.DEVNULL
except AttributeError:
    subprocess.DEVNULL = open(os.devnull, 'wb')

try:
    subprocess.check_output = subprocess.check_output
except AttributeError:
    def check_output(*popenargs, **kwargs):
        process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
        output, err = process.communicate()
        rc = process.poll()
        if rc:
            raise subprocess.CalledProcessError(rc, popenargs[0])
        return output

    subprocess.check_output = check_output
