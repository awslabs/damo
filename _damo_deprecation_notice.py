# SPDX-License-Identifier: GPL-2.0

import sys

def will_be_deprecated(feature, deadline, additional_notice=''):
    sys.stderr.write('\n'.join([
'',
'WARNING: %s will be deprecated by %s.' % (feature, deadline),
'    %s' % additional_notice,
'    Please report your usecase to Github issues[1], sj@kernel.org,',
'    damon@lists.linux.dev and/or linux-mm@kvack.org if you depend on those.',
'',
'    [1] https://github.com/awslabs/damo/issues',
'',
'']))

def deprecated(feature, deadline, do_exit=False, exit_code=1,
        additional_notice=''):
    sys.stderr.write('\n'.join([
'',
'WARNING: %s is deprecated.' % feature,
'    The support will be removed by %s.' % deadline,
'    %s' % additional_notice,
'    Please report your usecase to Github issues[1], sj@kernel.org,',
'    damon@lists.linux.dev and/or linux-mm@kvack.org if you depend on those.',
'',
'    [1] https://github.com/awslabs/damo/issues',
'',
'']))
    if do_exit:
        exit(exit_code)
