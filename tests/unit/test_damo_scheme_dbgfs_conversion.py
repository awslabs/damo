#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import unittest

import _test_damo_common

_test_damo_common.add_damo_dir_to_syspath()

import _damon
import _damon_args_schemes
import _damon_dbgfs

class TestDamoSchemeDbgfsConversion(unittest.TestCase):
    def test_conversion(self):
        inputs = {
                "darc1.damos": "# format is:\n# <min/max size> <min/max frequency (0-100)> <min/max age> <action> <limit_sz> <limit_ms>\n\n4K  max\t\tmin min\t\t5s max\t\tpageout\t\t500M 1s",
                "darc2.damos": "# For scheme version 2 (refer to comment of debugfs_scheme() in damo)\n\n# format is:\n# <min/max size> <min/max frequency (0-100)> <min/max age> <action> \\\n# <limit_sz> <limit_ms> <weight_sz> <weight_nr_accesses> <weight_age>\n\n4K  max\t\tmin min\t\t5s max\t\tpageout\t\t500M 1s\t\t0 3 7",
                "ethp.damos": "# format is: <min/max size> <min/max frequency (0-100)> <min/max age> <action>\n\nmin max\t\t5 max\t\tmin max\t\thugepage\n2M max\t\tmin min\t\t7s max\t\tnohugepage",
                "pdarc1-1.damos": "# format is:\n# <min/max size> <min/max frequency (0-100)> <min/max age> <action> <limit_sz> <limit_ms>\n\n4K  max\t\tmin min\t\t5s max\t\tpageout\t\t1G 1s",
                "pdarc1-2.damos": "# format is:\n# <min/max size> <min/max frequency (0-100)> <min/max age> <action> <limit_sz> <limit_ms>\n\n4K  max\t\tmin min\t\t5s max\t\tpageout\t\t5G 1s",
                "pdarc1-3.damos": "# format is:\n# <min/max size> <min/max frequency (0-100)> <min/max age> <action> <limit_sz> <limit_ms>\n\n4K  max\t\tmin min\t\t5s max\t\tpageout\t\t10G 1s",
                "pdarc2-1.damos": "# For scheme version 2 (refer to comment of debugfs_scheme() in damo)\n\n# format is:\n# <min/max size> <min/max frequency (0-100)> <min/max age> <action> \\\n# <limit_sz> <limit_ms> <weight_sz> <weight_nr_accesses> <weight_age>\n\n4K  max\t\tmin min\t\t5s max\t\tpageout\t\t1G 1s\t\t0 3 7",
                "pdarc2-2.damos": "# For scheme version 2 (refer to comment of debugfs_scheme() in damo)\n\n# format is:\n# <min/max size> <min/max frequency (0-100)> <min/max age> <action> \\\n# <limit_sz> <limit_ms> <weight_sz> <weight_nr_accesses> <weight_age>\n\n4K  max\t\tmin min\t\t5s max\t\tpageout\t\t5G 1s\t\t0 3 7",
                "pdarc2-3.damos": "# For scheme version 2 (refer to comment of debugfs_scheme() in damo)\n\n# format is:\n# <min/max size> <min/max frequency (0-100)> <min/max age> <action> \\\n# <limit_sz> <limit_ms> <weight_sz> <weight_nr_accesses> <weight_age>\n\n4K  max\t\tmin min\t\t5s max\t\tpageout\t\t10G 1s\t\t0 3 7",
                "pprcl.damos": "# format is: <min/max size> <min/max frequency (0-100)> <min/max age> <action>\n\n4K  max\t\tmin min\t\t5s max\t\tpageout",
                "prcl.damos": "# format is: <min/max size> <min/max frequency (0-100)> <min/max age> <action>\n\n4K  max\t\tmin min\t\t5s max\t\tpageout"
                }
        expects = {
                "darc1.damos.v0": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2",
                "darc1.damos.v1": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t524288000\t1000",
                "darc1.damos.v2": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t524288000\t1000\t0\t0\t0",
                "darc1.damos.v3": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t524288000\t1000\t0\t0\t0\t0\t0\t0\t0\t0",
                "darc1.damos.v4": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t0\t524288000\t1000\t0\t0\t0\t0\t0\t0\t0\t0",
                "darc2.damos.v0": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2",
                "darc2.damos.v1": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t524288000\t1000",
                "darc2.damos.v2": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t524288000\t1000\t0\t3\t7",
                "darc2.damos.v3": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t524288000\t1000\t0\t3\t7\t0\t0\t0\t0\t0",
                "darc2.damos.v4": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t0\t524288000\t1000\t0\t3\t7\t0\t0\t0\t0\t0",
                "ethp.damos.v0": "0\t18446744073709551615\t1\t20\t0\t184467440737095\t3\n2097152\t18446744073709551615\t0\t0\t70\t184467440737095\t4",
                "ethp.damos.v1": "0\t18446744073709551615\t1\t20\t0\t184467440737095\t3\t0\t18446744073709551615\n2097152\t18446744073709551615\t0\t0\t70\t184467440737095\t4\t0\t18446744073709551615",
                "ethp.damos.v2": "0\t18446744073709551615\t1\t20\t0\t184467440737095\t3\t0\t18446744073709551615\t0\t0\t0\n2097152\t18446744073709551615\t0\t0\t70\t184467440737095\t4\t0\t18446744073709551615\t0\t0\t0",
                "ethp.damos.v3": "0\t18446744073709551615\t1\t20\t0\t184467440737095\t3\t0\t18446744073709551615\t0\t0\t0\t0\t0\t0\t0\t0\n2097152\t18446744073709551615\t0\t0\t70\t184467440737095\t4\t0\t18446744073709551615\t0\t0\t0\t0\t0\t0\t0\t0",
                "ethp.damos.v4": "0\t18446744073709551615\t1\t20\t0\t184467440737095\t3\t0\t0\t18446744073709551615\t0\t0\t0\t0\t0\t0\t0\t0\n2097152\t18446744073709551615\t0\t0\t70\t184467440737095\t4\t0\t0\t18446744073709551615\t0\t0\t0\t0\t0\t0\t0\t0",
                "pdarc1-1.damos.v0": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2",
                "pdarc1-1.damos.v1": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t1073741824\t1000",
                "pdarc1-1.damos.v2": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t1073741824\t1000\t0\t0\t0",
                "pdarc1-1.damos.v3": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t1073741824\t1000\t0\t0\t0\t0\t0\t0\t0\t0",
                "pdarc1-1.damos.v4": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t0\t1073741824\t1000\t0\t0\t0\t0\t0\t0\t0\t0",
                "pdarc1-2.damos.v0": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2",
                "pdarc1-2.damos.v1": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t5368709120\t1000",
                "pdarc1-2.damos.v2": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t5368709120\t1000\t0\t0\t0",
                "pdarc1-2.damos.v3": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t5368709120\t1000\t0\t0\t0\t0\t0\t0\t0\t0",
                "pdarc1-2.damos.v4": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t0\t5368709120\t1000\t0\t0\t0\t0\t0\t0\t0\t0",
                "pdarc1-3.damos.v0": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2",
                "pdarc1-3.damos.v1": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t10737418240\t1000",
                "pdarc1-3.damos.v2": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t10737418240\t1000\t0\t0\t0",
                "pdarc1-3.damos.v3": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t10737418240\t1000\t0\t0\t0\t0\t0\t0\t0\t0",
                "pdarc1-3.damos.v4": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t0\t10737418240\t1000\t0\t0\t0\t0\t0\t0\t0\t0",
                "pdarc2-1.damos.v0": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2",
                "pdarc2-1.damos.v1": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t1073741824\t1000",
                "pdarc2-1.damos.v2": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t1073741824\t1000\t0\t3\t7",
                "pdarc2-1.damos.v3": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t1073741824\t1000\t0\t3\t7\t0\t0\t0\t0\t0",
                "pdarc2-1.damos.v4": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t0\t1073741824\t1000\t0\t3\t7\t0\t0\t0\t0\t0",
                "pdarc2-2.damos.v0": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2",
                "pdarc2-2.damos.v1": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t5368709120\t1000",
                "pdarc2-2.damos.v2": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t5368709120\t1000\t0\t3\t7",
                "pdarc2-2.damos.v3": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t5368709120\t1000\t0\t3\t7\t0\t0\t0\t0\t0",
                "pdarc2-2.damos.v4": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t0\t5368709120\t1000\t0\t3\t7\t0\t0\t0\t0\t0",
                "pdarc2-3.damos.v0": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2",
                "pdarc2-3.damos.v1": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t10737418240\t1000",
                "pdarc2-3.damos.v2": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t10737418240\t1000\t0\t3\t7",
                "pdarc2-3.damos.v3": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t10737418240\t1000\t0\t3\t7\t0\t0\t0\t0\t0",
                "pdarc2-3.damos.v4": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t0\t10737418240\t1000\t0\t3\t7\t0\t0\t0\t0\t0",
                "pprcl.damos.v0": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2",
                "pprcl.damos.v1": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t0\t18446744073709551615",
                "pprcl.damos.v2": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t0\t18446744073709551615\t0\t0\t0",
                "pprcl.damos.v3": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t0\t18446744073709551615\t0\t0\t0\t0\t0\t0\t0\t0",
                "pprcl.damos.v4": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t0\t0\t18446744073709551615\t0\t0\t0\t0\t0\t0\t0\t0",
        "prcl.damos.v0": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2",
                "prcl.damos.v1": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t0\t18446744073709551615",
                "prcl.damos.v2": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t0\t18446744073709551615\t0\t0\t0",
                "prcl.damos.v3": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t0\t18446744073709551615\t0\t0\t0\t0\t0\t0\t0\t0",
                "prcl.damos.v4": "4096\t18446744073709551615\t0\t0\t50\t184467440737095\t2\t0\t0\t18446744073709551615\t0\t0\t0\t0\t0\t0\t0\t0"
                            }
        intervals = _damon.DamonIntervals('5ms', '100ms', '1s')
        for input_name, input_scheme in inputs.items():
            for version in range(0, 5):
                damos_list, err = _damon_args_schemes.damo_schemes_to_damos(
                        input_scheme)
                self.assertEqual(err, None)
                lines = []
                for damos in damos_list:
                    lines.append(_damon_dbgfs.damos_to_debugfs_input(damos,
                        intervals, version))
                self.assertEqual('\n'.join(lines),
                        expects['%s.v%d' % (input_name, version)])

if __name__ == '__main__':
    unittest.main()
