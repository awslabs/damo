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
    target_snapshots = None    # {target_id: [snapshot]}

    def __init__(self):
        self.target_snapshots = {}

def record_to_damon_result(file_path, f, fmt_version, max_secs):
    result = None
    parse_start_time = None

    if f == None:
        f = open(file_path, 'rb')

        # read record format version
        mark = f.read(16)
        if mark == b'damon_recfmt_ver':
            fmt_version = struct.unpack('i', f.read(4))[0]
        else:
            fmt_version = 0
            f.seek(0)
    elif not fmt_version:
        print('fmt_version is not given')
        exit(1)

    result = DAMONResult()

    while True:
        timebin = f.read(16)
        if len(timebin) != 16:
            if max_secs == None:
                f.close()
            break
        sec = struct.unpack('l', timebin[0:8])[0]
        nsec = struct.unpack('l', timebin[8:16])[0]
        end_time = sec * 1000000000 + nsec

        if not parse_start_time:
            parse_start_time = end_time
        elif max_secs != None and (
                end_time - parse_start_time > max_secs * 1000000000):
            f.seek(-16, 1)
            break

        nr_tasks = struct.unpack('I', f.read(4))[0]
        for t in range(nr_tasks):
            if fmt_version == 1:
                target_id = struct.unpack('i', f.read(4))[0]
            else:
                target_id = struct.unpack('L', f.read(8))[0]

            if not target_id in result.target_snapshots:
                result.target_snapshots[target_id] = []
            target_snapshots = result.target_snapshots[target_id]
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

    return result, f, fmt_version

def perf_script_to_damon_result(file_path, f, max_secs):
    result = None
    nr_read_regions = 0
    parse_start_time = None

    if not f:
        f = open(file_path, 'r')

    for line in f:
        line = line.strip()
        '''
        example line is as below:

        kdamond.0  4452 [000] 82877.315633: damon:damon_aggregated: \
                target_id=18446623435582458880 nr_regions=17 \
                140731667070976-140731668037632: 0 3

        Note that the last field is not in the mainline but a patch[1] for it
        is posted.

        [1] https://lore.kernel.org/linux-mm/df8d52f1fb2f353a62ff34dc09fe99e32ca1f63f.1636610337.git.xhao@linux.alibaba.com/
        '''

        fields = line.strip().split()
        if not len(fields) in [9, 10]:
            continue
        if fields[4] != 'damon:damon_aggregated:':
            continue
        end_time = int(float(fields[3][:-1]) * 1000000000)
        if not result:
            result = DAMONResult()
        if parse_start_time == None:
            parse_start_time = end_time
        elif max_secs != None and (
                end_time - parse_start_time > max_secs * 1000000000):
            # reverse seek of text file is not supported, we simply remove
            # over-read line.
            break

        target_id = int(fields[5].split('=')[1])

        if not target_id in result.target_snapshots:
            result.target_snapshots[target_id] = []
        target_snapshots = result.target_snapshots[target_id]
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

    if max_secs == None:
        f.close()
    return result, f

def parse_damon_result_for(result_file, file_type, f, fmt_version, max_secs):
    if not file_type:
        file_type = 'record'
        output = subprocess.check_output('file -b \'%s\'' % result_file,
                shell=True, executable='/bin/bash').decode().strip()
        if output == 'ASCII text':
            file_type = 'perf_script'

    if file_type == 'record':
        result, f, fmt_version = record_to_damon_result(result_file,
                f, fmt_version, max_secs)
    elif file_type == 'perf_script':
        result, f = perf_script_to_damon_result(result_file, f, max_secs)
        fmt_version = None
    else:
        print('unknown result file type: %s (%s)' % (file_type, result_file))
        return None

    for snapshots in result.target_snapshots.values():
        if len(snapshots) < 2:
            break
        if not result.start_time:
            end_time = snapshots[-1].end_time
            start_time = snapshots[0].end_time
            nr_snapshots = len(snapshots) - 1
            snapshot_time = float(end_time - start_time) / nr_snapshots

            result.start_time = start_time - snapshot_time
            result.end_time = end_time
            result.nr_snapshots = nr_snapshots + 1

        snapshots[0].start_time = snapshots[0].end_time - snapshot_time

    return result, f, fmt_version

def parse_damon_result(result_file, file_type):
    result, f, fmt_version = parse_damon_result_for(result_file, file_type,
            None, None, None)
    f.close()
    return result

def write_damon_record(result, file_path, format_version):
    with open(file_path, 'wb') as f:
        f.write(b'damon_recfmt_ver')
        f.write(struct.pack('i', format_version))

        for snapshot_idx in range(result.nr_snapshots):
            for tid in result.target_snapshots:
                snapshot = result.target_snapshots[tid][snapshot_idx]
                f.write(struct.pack('l', snapshot.end_time // 1000000000))
                f.write(struct.pack('l', snapshot.end_time % 1000000000))

                f.write(struct.pack('I', 1))

                if format_version == 1:
                    f.write(struct.pack('i', snapshot.target_id))
                else:
                    f.write(struct.pack('L', snapshot.target_id))

                f.write(struct.pack('I', len(snapshot.regions)))
                for region in snapshot.regions:
                    f.write(struct.pack('L', region.start))
                    f.write(struct.pack('L', region.end))
                    f.write(struct.pack('I', region.nr_accesses))

def write_damon_perf_script(result, file_path):
    '''
    Example of the normal perf script output:

    kdamond.0  4452 [000] 82877.315633: damon:damon_aggregated: \
            target_id=18446623435582458880 nr_regions=17 \
            140731667070976-140731668037632: 0 3
    '''

    with open(file_path, 'w') as f:
        for snapshot_idx in range(result.nr_snapshots):
            for tid in result.target_snapshots:
                snapshot = result.target_snapshots[tid][snapshot_idx]
                for region in snapshot.regions:
                    f.write(' '.join(['kdamond.x', 'xxxx', 'xxxx',
                        '%f:' % (snapshot.end_time / 1000000000),
                        'damon:damon_aggregated:',
                        'target_id=%s' % snapshot.target_id,
                        'nr_regions=%d' % len(snapshot.regions),
                        '%d-%d: %d x' % (region.start, region.end,
                            region.nr_accesses)]) + '\n')

def write_damon_result(result, file_path, file_type):
    if file_type == 'record':
        write_damon_record(result, file_path, 2)
    elif file_type == 'perf_script':
        write_damon_perf_script(result, file_path)
    else:
        print('unsupported file type: %s' % file_type)

def regions_intersect(r1, r2):
    return not (r1.end <= r2.start or r2.end <= r1.start)

def add_region(regions, region, nr_acc_to_add):
    for r in regions:
        if regions_intersect(r, region):
            if not r in nr_acc_to_add:
                nr_acc_to_add[r] = 0
            nr_acc_to_add[r] = max(nr_acc_to_add[r], region.nr_accesses)

            new_regions = []
            if region.start < r.start:
                new_regions.append(DAMONRegion(
                    region.start, r.start, region.nr_accesses))
            if r.end < region.end:
                new_regions.append(DAMONRegion(
                        r.end, region.end, region.nr_accesses))

            for new_r in new_regions:
                add_region(regions, new_r, nr_acc_to_add)
            return
    regions.append(region)

def aggregate_snapshots(snapshots):
    new_regions = []
    for snapshot in snapshots:
        nr_acc_to_add = {}
        for region in snapshot.regions:
            add_region(new_regions, region, nr_acc_to_add)
        for region in nr_acc_to_add:
            region.nr_accesses += nr_acc_to_add[region]

    new_snapshot = DAMONSnapshot(snapshots[0].start_time,
            snapshots[-1].end_time, snapshots[0].target_id)
    new_snapshot.regions = new_regions
    return new_snapshot
