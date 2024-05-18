#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import os
import sys

def test_input_expects(testcase, function, input_expects):
    for input_ in input_expects:
        testcase.assertEqual(function(input_), input_expects[input_])

def test_input_expects_funcs(testcase, functions, input_expects):
    for input_ in input_expects:
        for idx, expect in enumerate(input_expects[input_]):
            test_input_expects(testcase, functions[idx], {input_: expect})

def add_damo_dir_to_syspath():
    bindir = os.path.dirname(os.path.realpath(__file__))
    damo_dir = os.path.join(bindir, '..', '..', 'src')
    sys.path.append(damo_dir)
