#!/usr/bin/env python3

import struct

class DAMONRegion:
    start = None
    end = None
    nr_accesses = None

    def __init__(self, start, end, nr_accesses):
        self.start = start
        self.end = end
        self.nr_accesses = nr_accesses

class DAMONSnapshot:
    monitored_time = None
    target_id = None
    regions = None

    def __init__(self, monitored_time, target_id):
        self.monitored_time = monitored_time
        self.target_id = target_id
        self.regions = []

class DAMONResult:
    start_time = None
    snapshots = None

    def __init__(self, start_time):
        self.start_time = start_time
        self.snapshots = []

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

        while True:
            timebin = f.read(16)
            if len(timebin) != 16:
                break
            sec = struct.unpack('l', timebin[0:8])[0]
            nsec = struct.unpack('l', timebin[8:16])[0]
            time = sec * 1000000000 + nsec
            if not result:
                result = DAMONResult(time)
            nr_tasks = struct.unpack('I', f.read(4))[0]
            for t in range(nr_tasks):
                if fmt_version == 1:
                    target_id = struct.unpack('i', f.read(4))[0]
                else:
                    target_id = struct.unpack('L', f.read(8))[0]
                snapshot = DAMONSnapshot(time, target_id)
                nr_regions = struct.unpack('I', f.read(4))[0]
                for r in range(nr_regions):
                    start_addr = struct.unpack('L', f.read(8))[0]
                    end_addr = struct.unpack('L', f.read(8))[0]
                    nr_accesses = struct.unpack('I', f.read(4))[0]
                    region = DAMONRegion(start_addr, end_addr, nr_accesses)
                    snapshot.regions.append(region)
                result.snapshots.append(snapshot)
    return result
