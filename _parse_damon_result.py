#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import struct
import subprocess

class DAMONRegion:
    start = None
    end = None
    nr_accesses = None

    def __init__(self, start, end, nr_accesses):
        self.start = start
        self.end = end
        self.nr_accesses = nr_accesses

class DAMONSnapshot:
    start_time = None
    end_time = None
    target_id = None
    regions = None

    def __init__(self, start_time, end_time, target_id):
        self.start_time = start_time
        self.end_time = end_time
        self.target_id = target_id
        self.regions = []

class DAMONResult:
    start_time = None
    end_time = None
    nr_snapshots = None
    snapshots = None    # {target: [snapshot]}

    def __init__(self):
        self.snapshots = {}

def record_to_damon_result(file_path):
    result = None

    with open(file_path, 'rb') as f:
        # read record format version
        mark = f.read(16)
        if mark == b'damon_recfmt_ver':
            fmt_version = struct.unpack('i', f.read(4))[0]
        else:
            fmt_version = 0
            f.seek(0)

        result = DAMONResult()

        while True:
            timebin = f.read(16)
            if len(timebin) != 16:
                break
            sec = struct.unpack('l', timebin[0:8])[0]
            nsec = struct.unpack('l', timebin[8:16])[0]
            end_time = sec * 1000000000 + nsec
            nr_tasks = struct.unpack('I', f.read(4))[0]
            for t in range(nr_tasks):
                if fmt_version == 1:
                    target_id = struct.unpack('i', f.read(4))[0]
                else:
                    target_id = struct.unpack('L', f.read(8))[0]

                if not target_id in result.snapshots:
                    result.snapshots[target_id] = []
                target_snapshots = result.snapshots[target_id]
                if len(target_snapshots) == 0:
                    start_time = None
                else:
                    start_time = target_snapshots[-1].end_time

                snapshot = DAMONSnapshot(start_time, end_time, target_id)
                nr_regions = struct.unpack('I', f.read(4))[0]
                for r in range(nr_regions):
                    start_addr = struct.unpack('L', f.read(8))[0]
                    end_addr = struct.unpack('L', f.read(8))[0]
                    nr_accesses = struct.unpack('I', f.read(4))[0]
                    region = DAMONRegion(start_addr, end_addr, nr_accesses)
                    snapshot.regions.append(region)
                target_snapshots.append(snapshot)

    return result

def perf_script_to_damon_result(perf_script_file):
    result = None
    nr_read_regions = 0

    with open(perf_script_file, 'r') as f:
        content = f.read().split('\n')

    for line in content:
        '''
        example line is as below:

        kdamond.0  4452 [000] 82877.315633: damon:damon_aggregated: \
                target_id=18446623435582458880 nr_regions=17 \
                140731667070976-140731668037632: 0
        '''

        fields = line.strip().split()
        if len(fields) != 9:
            continue
        if fields[4] != 'damon:damon_aggregated:':
            continue
        end_time = int(float(fields[3][:-1]) * 1000000)
        if not result:
            result = DAMONResult()

        target_id = int(fields[5].split('=')[1])

        if not target_id in result.snapshots:
            result.snapshots[target_id] = []
        target_snapshots = result.snapshots[target_id]
        if len(target_snapshots) == 0:
            start_time = None
        else:
            start_time = target_snapshots[-1].end_time

        nr_regions = int(fields[6].split('=')[1])
        addrs = [int(x) for x in fields[7][:-1].split('-')]
        nr_accesses = int(fields[8])

        if nr_read_regions == 0:
            snapshot = DAMONSnapshot(start_time, end_time, target_id)
            target_snapshots.append(snapshot)

        snapshot = target_snapshots[-1]
        snapshot.regions.append(DAMONRegion(addrs[0], addrs[1], nr_accesses))

        nr_read_regions += 1
        if nr_read_regions == nr_regions:
            nr_read_regions = 0

    return result

def parse_damon_result(result_file, file_type):
    if not file_type:
        output = subprocess.check_output('file -b \'%s\'' % result_file,
                shell=True, executable='/bin/bash').decode().strip()
        if output == 'data':
            file_type = 'record'
        elif output == 'ASCII text':
            file_type = 'perf_script'
        else:
            print('cannot figure out the type of result file')
            return None

    if file_type == 'record':
        result = record_to_damon_result(result_file)
    elif file_type == 'perf_script':
        result = perf_script_to_damon_result(result_file)
    else:
        print('unknown result file type: %s' % file_type)
        return None

    for snapshots in result.snapshots.values():
        if not result.start_time:
            end_time = snapshots[-1].end_time
            start_time = snapshots[0].end_time
            nr_snapshots = len(snapshots) - 1
            snapshot_time = (end_time - start_time) / nr_snapshots

            result.start_time = start_time - snapshot_time
            result.end_time = end_time
            result.nr_snapshots = nr_snapshots + 1

        snapshots[0].start_time = snapshots[0].end_time - snapshot_time

    return result
