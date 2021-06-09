#!/usr/bin/env python3

import time

sz_stair = 10 * 1024 * 1024
nr_stairs = 2
time_for_stair = 3

def main():
    stairs = []
    for i in range(nr_stairs):
        stairs.append(bytearray(sz_stair))

    for i in range(nr_stairs):
        stair = stairs[i]
        start = time.time()
        while time.time() - start < time_for_stair:
            for j in range(sz_stair):
                stair[j] = i

if __name__ == '__main__':
    main()
