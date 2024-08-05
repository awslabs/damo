# SPDX-License-Identifier: GPL-2.0

import collections
import sys

try:
    import yaml
except ModuleNotFoundError as e:
    # do nothing.  The yaml using functions should handle the exception
    # properly.
    pass

'''
damo's data structures including Kdamond uses collections.OrderedDict for
some to_kvpairs() outputs.  yaml.dump() adds constructor comments for those
like below.

    kdamonds:
    - !!python/object/apply:collections.OrderedDict
      - - - state
          - null
        - - pid
          - null

yaml.safe_load(), which is used to reconstruct the data structures from some
points including _damon_args to read the yaml output again, fails at parsing
it.  To support it, we should use yaml.load() with a specific loader.

However, we use OrderedDict to make json or yaml-like dumped output keeps the
order.  That's for letting it easy to read by human beings.  Here, the added
constructor comment and slightly changed format are for machines.  Also
from_kvpairs() methods for the data structures don't really care about the
orders and the type.

So, adding the handling on dumping part instead of the loading part would make
the result simpler while it all works seamlessly.  Use a custom dumper that
prints OrderedDict as normal dict.
'''
def dump(kvpairs):
    def ordered_dict_representer(dumper, ordered_dict):
        # represnet collections.OrderedDict object as normal dict, but while
        # keeping the dumped order; the order will be ignored when loaded
        # again, but that's not a problem for Kdamonds.
        return dumper.represent_dict(ordered_dict.items())

    class OrderedDumper(yaml.SafeDumper):
        # Same to safe dumper but represent OrderedDict using
        # ordered_dict_representer
        pass

    OrderedDumper.add_representer(
            collections.OrderedDict, ordered_dict_representer)

    if not 'yaml' in sys.modules:
        return None, 'yaml module is not imported'

    return yaml.dump(kvpairs, Dumper=OrderedDumper, default_flow_style=False,
                     sort_keys=False), None
