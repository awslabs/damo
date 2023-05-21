# SPDX-License-Identifier: GPL-2.0

import sys

def deprecated(feature, deadline, additional_notice=''):
    sys.stderr.write('\n'.join([
'WARNING: %s is deprecated.' % feature,
'    The support will be removed by %s.' % deadline,
'    %s' % additional_notice,
'    Please report your usecase to sj@kernel.org, damon@lists.linux.dev and',
'    linux-mm@kvack.org if you depend on those.']))
