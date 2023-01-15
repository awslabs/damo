#!/usr/bin/env python3

import argparse
import json

import _damon
import _damon_args

def main():
    parser = argparse.ArgumentParser()
    _damon_args.set_explicit_target_argparser(parser)
    args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    kdamonds, err = _damon_args.kdamonds_from_damon_args(args)
    if err:
        print('creating kdamonds from arguments failed (%s)' % err)
        exit(1)
    kvpairs = [k.to_kvpairs() for k in kdamonds]
    print(json.dumps(kvpairs, indent=4, sort_keys=True))

if __name__ == '__main__':
    main()
