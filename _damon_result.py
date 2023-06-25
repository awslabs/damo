# SPDX-License-Identifier: GPL-2.0

import collections
import json
import os
import signal
import struct
import subprocess
import time
import zlib

import _damo_deprecation_notice
import _damo_fmt_str
import _damon

PERF = 'perf'
PERF_EVENT = 'damon:damon_aggregated'

class DamonSnapshot:
    '''
    Contains a snapshot of data access monitoring results
    '''
    start_time = None
    end_time = None
    regions = None

    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time
        self.regions = []

    @classmethod
    def from_kvpairs(cls, kv):
        snapshot = DamonSnapshot(_damo_fmt_str.text_to_ns(kv['start_time']),
                _damo_fmt_str.text_to_ns(kv['end_time']))
        snapshot.regions = [_damon.DamonRegion.from_kvpairs(r)
                for r in kv['regions']]
        return snapshot

    def to_kvpairs(self, raw=False):
        return collections.OrderedDict([
            ('start_time', _damo_fmt_str.format_time_ns_exact(
                self.start_time, raw)),
            ('end_time', _damo_fmt_str.format_time_ns_exact(
                self.end_time, raw)),
            ('regions', [r.to_kvpairs() for r in self.regions])])

class DamonRecord:
    '''
    Contains data access monitoring results for single target
    '''
    kdamond_idx = None
    context_idx = None
    intervals = None
    scheme_idx = None
    target_id = None
    snapshots = None

    def __init__(self, kd_idx, ctx_idx, intervals, scheme_idx, target_id):
        self.kdamond_idx = kd_idx
        self.context_idx = ctx_idx
        self.intervals = intervals
        self.scheme_idx = scheme_idx
        self.target_id = target_id
        self.snapshots = []

    @classmethod
    def from_kvpairs(cls, kv):
        for keyword in ['kdamond_idx', 'context_idx', 'intervals',
                'scheme_idx']:
            if not keyword in kv:
                kv[keyword] = None

        record = DamonRecord(kv['kdamond_idx'], kv['context_idx'],
                _damon.DamonIntervals.from_kvpairs(kv['intervals'])
                if kv['intervals'] != None else None,
                kv['scheme_idx'], kv['target_id'])
        record.snapshots = [DamonSnapshot.from_kvpairs(s)
                for s in kv['snapshots']]

        return record

    def to_kvpairs(self, raw=False):
        ordered_dict = collections.OrderedDict()
        ordered_dict['kdamond_idx'] = self.kdamond_idx
        ordered_dict['context_idx'] = self.context_idx
        ordered_dict['intervals'] = (self.intervals.to_kvpairs(raw)
                if self.intervals != None else None)
        ordered_dict['scheme_idx'] = self.scheme_idx
        ordered_dict['target_id'] = self.target_id
        ordered_dict['snapshots'] = [s.to_kvpairs(raw) for s in self.snapshots]
        return ordered_dict

# for monitoring results manipulation

def regions_intersect(r1, r2):
    return not (r1.end <= r2.start or r2.end <= r1.start)

def add_region(regions, region, nr_acc_to_add):
    for r in regions:
        if regions_intersect(r, region):
            if not r in nr_acc_to_add:
                nr_acc_to_add[r] = 0
            nr_acc_to_add[r] = max(nr_acc_to_add[r],
                    region.nr_accesses.samples)

            new_regions = []
            if region.start < r.start:
                new_regions.append(_damon.DamonRegion(
                    region.start, r.start,
                    region.nr_accesses.samples, _damon.unit_samepls,
                    region.age.aggr_intervals, _damon.unit_aggr_intervals))
            if r.end < region.end:
                new_regions.append(_damon.DamonRegion(
                        r.end, region.end,
                        region.nr_accesses.samples, _damon.unit_samples,
                        region.age.aggr_intervals,
                        _damon.unit_aggr_intervals))

            for new_r in new_regions:
                add_region(regions, new_r, nr_acc_to_add)
            return
    regions.append(region)

def aggregate_snapshots(snapshots):
    new_regions = []
    for snapshot in snapshots:
        # Suppose the first snapshot has a region 1-10:5, and the second
        # snapshot has two regions, 1-5:2, 5-10: 4.  Aggregated snapshot should
        # be 1-10:9.  That is, we should add maximum nr_accesses of
        # intersecting regions.  nr_acc_to_add contains the information.
        nr_acc_to_add = {}
        for region in snapshot.regions:
            add_region(new_regions, region, nr_acc_to_add)
        for region in nr_acc_to_add:
            region.nr_accesses.samples += nr_acc_to_add[region]
            region.nr_accesses.val = region.nr_accesses.samples
            region.nr_accesses.unit = _damon.unit_samples

    new_snapshot = DamonSnapshot(snapshots[0].start_time,
            snapshots[-1].end_time)
    new_snapshot.regions = new_regions
    return new_snapshot

def adjusted_snapshots(snapshots, aggregate_interval_us):
    adjusted = []
    to_aggregate = []
    for snapshot in snapshots:
        to_aggregate.append(snapshot)
        interval_ns = to_aggregate[-1].end_time - to_aggregate[0].start_time
        if interval_ns >= aggregate_interval_us * 1000:
            adjusted.append(aggregate_snapshots(to_aggregate))
            to_aggregate = []
    return adjusted

def adjust_records(records, aggregate_interval, nr_snapshots_to_skip):
    for record in records:
        if record.intervals != None:
            record.intervals.aggr = aggregate_interval
        record.snapshots = adjusted_snapshots(
                record.snapshots[nr_snapshots_to_skip:], aggregate_interval)

# For reading monitoring results from a file

def read_record_format_version(f):
    # read record format version
    mark = f.read(16)
    if mark == b'damon_recfmt_ver':
        return struct.unpack('i', f.read(4))[0]
    else:
        f.seek(0)
        return 0

def read_end_time_from_record_file(f):
    timebin = f.read(16)
    if len(timebin) != 16:
        return None
    sec = struct.unpack('l', timebin[0:8])[0]
    nsec = struct.unpack('l', timebin[8:16])[0]
    end_time = sec * 1000000000 + nsec
    return end_time

def read_snapshot_from_record_file(f, start_time, end_time):
    snapshot = DamonSnapshot(start_time, end_time)
    nr_regions = struct.unpack('I', f.read(4))[0]
    for r in range(nr_regions):
        start_addr = struct.unpack('L', f.read(8))[0]
        end_addr = struct.unpack('L', f.read(8))[0]
        nr_accesses = struct.unpack('I', f.read(4))[0]
        region = _damon.DamonRegion(start_addr, end_addr,
                nr_accesses, _damon.unit_samples,
                None, _damon.unit_aggr_intervals)
        snapshot.regions.append(region)
    return snapshot

# if number of snapshots is one and the file type is record or perf script,
# write_damon_records() adds a fake snapshot for snapshot start time deduction.
def is_fake_snapshot(snapshot):
    if len(snapshot.regions) != 1:
        return False
    r = snapshot.regions[0]
    return (r.start == 0 and r.end == 0 and
            r.nr_accesses.samples == -1 and r.age.aggr_intervals == -1)

def set_first_snapshot_start_time(records):
    for record in records:
        snapshots = record.snapshots
        if len(snapshots) < 2:
            break
        end_time = snapshots[-1].end_time
        start_time = snapshots[0].end_time
        nr_snapshots = len(snapshots) - 1
        snapshot_time = float(end_time - start_time) / nr_snapshots
        snapshots[0].start_time = snapshots[0].end_time - snapshot_time

        if is_fake_snapshot(snapshots[-1]):
            del record.snapshots[-1]

def warn_record_type_deprecation():
    _damo_deprecation_notice.will_be_deprecated(
            feature='\'record\' file type support',
            deadline='2023-Q3',
            additional_notice='use json_compressed type instead.')

def record_of(target_id, records, intervals):
    for record in records:
        if record.target_id == target_id:
            return record
    record = DamonRecord(None, None, intervals, None, target_id)
    records.append(record)
    return record

def parse_binary_format_record(file_path, monitoring_intervals):
    warn_record_type_deprecation()
    with open(file_path, 'rb') as f:
        fmt_version = read_record_format_version(f)
        records = []
        while True:
            end_time = read_end_time_from_record_file(f)
            if end_time == None:
                break

            nr_tasks = struct.unpack('I', f.read(4))[0]
            for t in range(nr_tasks):
                if fmt_version == 1:
                    target_id = struct.unpack('i', f.read(4))[0]
                else:
                    target_id = struct.unpack('L', f.read(8))[0]

                record = record_of(target_id, records, monitoring_intervals)
                if len(record.snapshots) == 0:
                    start_time = None
                else:
                    start_time = record.snapshots[-1].end_time
                    if end_time < start_time:
                        return None, 'snapshot is not sorted by time'
                try:
                    snapshot = read_snapshot_from_record_file(f,
                            start_time, end_time)
                except Exception as e:
                    return None, 'snapshot reading failead: %s' % e
                record.snapshots.append(snapshot)

    set_first_snapshot_start_time(records)
    return records, None

def parse_perf_script_line(line):
        '''
        example line is as below:

        kdamond.0  4452 [000] 82877.315633: damon:damon_aggregated: \
                target_id=18446623435582458880 nr_regions=17 \
                140731667070976-140731668037632: 0 3

        Note that the last field is not in the early version[1].

        [1] https://lore.kernel.org/linux-mm/df8d52f1fb2f353a62ff34dc09fe99e32ca1f63f.1636610337.git.xhao@linux.alibaba.com/
        '''
        fields = line.strip().split()
        if not len(fields) in [9, 10]:
            return None, None, None, None
        if fields[4] != 'damon:damon_aggregated:':
            return None, None, None, None

        end_time = int(float(fields[3][:-1]) * 1000000000)
        target_id = int(fields[5].split('=')[1])
        nr_regions = int(fields[6].split('=')[1])

        start_addr, end_addr = [int(x) for x in fields[7][:-1].split('-')]
        nr_accesses = int(fields[8])
        if len(fields) == 10:
            age = int(fields[9])
        else:
            age = None
        region = _damon.DamonRegion(start_addr, end_addr,
                nr_accesses, _damon.unit_samples,
                age, _damon.unit_aggr_intervals)

        return region, end_time, target_id, nr_regions

def parse_perf_script(script_output, monitoring_intervals):
    records = []
    snapshot = None

    for line in script_output.split('\n'):
        region, end_time, target_id, nr_regions = parse_perf_script_line(line)
        if region == None:
            continue

        record = record_of(target_id, records, monitoring_intervals)
        if len(record.snapshots) == 0:
            start_time = None
        else:
            start_time = record.snapshots[-1].end_time
            if start_time > end_time:
                return None, 'trace is not time-sorted'

        if snapshot == None:
            snapshot = DamonSnapshot(start_time, end_time)
            record.snapshots.append(snapshot)
        snapshot = record.snapshots[-1]
        snapshot.regions.append(region)

        if len(snapshot.regions) == nr_regions:
            snapshot = None

    set_first_snapshot_start_time(records)
    return records, None

def set_perf_path(perf_path):
    global PERF
    PERF = perf_path

    # Test perf record for damon event
    err = None
    try:
        subprocess.check_output(['which', PERF])
        try:
            subprocess.check_output(
                    [PERF, 'record', '-e', PERF_EVENT, '--', 'sleep', '0'],
                    stderr=subprocess.PIPE)
        except:
            err = 'perf record not working with "%s"' % PERF
    except:
        err = 'perf not found at "%s"' % PERF
    return err

def parse_json(json_str):
    kvpairs = json.loads(json_str)
    return [DamonRecord.from_kvpairs(kvp) for kvp in kvpairs]

def parse_json_compressed(result_file):
    with open(result_file, 'rb') as f:
        compressed = f.read()
    decompressed = zlib.decompress(compressed).decode()
    return parse_json(decompressed)

def parse_json_file(record_file):
    with open(record_file) as f:
        json_str = f.read()
    return parse_json(json_str)

def parse_records_file(result_file, monitoring_intervals=None):
    '''
    Return monitoring results records and error string
    '''

    file_type = subprocess.check_output(
            ['file', '-b', result_file]).decode().strip()
    if file_type == 'JSON data':
        try:
            return parse_json_file(result_file), None
        except Exception as e:
            return None, 'failed parsing json file (%s)' % e
    if file_type == 'zlib compressed data':
        try:
            return parse_json_compressed(result_file), None
        except Exception as e:
            return None, 'failed parsing json compressed file (%s)' % e

    perf_script_output = None
    if file_type == 'ASCII text':
        with open(result_file, 'r') as f:
            perf_script_output = f.read()
    else:
        # might be perf data
        try:
            with open(os.devnull, 'w') as fnull:
                perf_script_output = subprocess.check_output(
                        [PERF, 'script', '-i', result_file],
                        stderr=fnull).decode()
        except:
            # Should be record format file
            pass
    if perf_script_output != None:
        return parse_perf_script(perf_script_output, monitoring_intervals)
    return parse_binary_format_record(result_file, monitoring_intervals)

# for writing monitoring results to a file

def write_json_compressed(records, file_path):
    json_str = json.dumps([r.to_kvpairs(raw=True) for r in records], indent=4)
    compressed = zlib.compress(json_str.encode())
    with open(file_path, 'wb') as f:
        f.write(compressed)

def write_json(records, file_path):
    json_str = json.dumps([r.to_kvpairs(raw=True) for r in records], indent=4)
    with open(file_path, 'w') as f:
        f.write(json_str)

def add_fake_snapshot_if_needed(records):
    '''
    perf and record file format stores only snapshot end time.  For a record
    having only single snapshot, hence, the reader of the files cannot knwo the
    start time of the snapshot.  Add a fake snapshot for the case.
    '''

    for record in records:
        snapshots = record.snapshots
        if len(snapshots) != 1:
            continue
        snapshot = snapshots[0]
        snap_duration = snapshot.end_time - snapshot.start_time
        fake_snapshot = DamonSnapshot(snapshot.end_time,
                snapshot.end_time + snap_duration)
        # -1 nr_accesses.samples / -1 age.aggr_intervals means fake
        fake_snapshot.regions = [_damon.DamonRegion(0, 0,
            -1, _damon.unit_samples, -1, _damon.unit_aggr_intervals)]
        snapshots.append(fake_snapshot)

def write_binary(records, file_path, format_version):
    warn_record_type_deprecation()
    add_fake_snapshot_if_needed(records)

    with open(file_path, 'wb') as f:
        f.write(b'damon_recfmt_ver')
        f.write(struct.pack('i', format_version))

        for record in records:
            snapshots = record.snapshots
            for snapshot in snapshots:
                f.write(struct.pack('l', snapshot.end_time // 1000000000))
                f.write(struct.pack('l', snapshot.end_time % 1000000000))

                f.write(struct.pack('I', 1))

                if format_version == 1:
                    f.write(struct.pack('i', record.target_id))
                else:
                    f.write(struct.pack('L', record.target_id))

                f.write(struct.pack('I', len(snapshot.regions)))
                for region in snapshot.regions:
                    f.write(struct.pack('L', region.start))
                    f.write(struct.pack('L', region.end))
                    f.write(struct.pack('I', region.nr_accesses.samples))

def write_perf_script(records, file_path):
    '''
    Example of the normal perf script output:

    kdamond.0  4452 [000] 82877.315633: damon:damon_aggregated: \
            target_id=18446623435582458880 nr_regions=17 \
            140731667070976-140731668037632: 0 3
    '''

    add_fake_snapshot_if_needed(records)
    with open(file_path, 'w') as f:
        for record in records:
            snapshots = record.snapshots
            for snapshot in snapshots:
                for region in snapshot.regions:
                    f.write(' '.join(['kdamond.x', 'xxxx', 'xxxx',
                        '%f:' % (snapshot.end_time / 1000000000.0),
                        'damon:damon_aggregated:',
                        'target_id=%s' % record.target_id,
                        'nr_regions=%d' % len(snapshot.regions),
                        '%d-%d: %d %s' % (region.start, region.end,
                            region.nr_accesses.samples,
                            region.age.aggr_intervals)]) + '\n')

def parse_file_permission_str(file_permission_str):
    try:
        file_permission = int(file_permission_str, 8)
    except Exception as e:
        return None, 'parsing failed (%s)' % e
    if file_permission < 0o0 or file_permission > 0o777:
        return None, 'out of available permission range'
    return file_permission, None

file_type_record = 'record'             # damo defined binary format
file_type_perf_script = 'perf_script'   # perf script output
file_type_perf_data = 'perf_data'       # perf record result file
file_type_json = 'json'                 # list of DamonRecord objects in json
file_type_json_compressed = 'json_compressed'

file_types = [file_type_json_compressed, file_type_json, file_type_perf_script,
        file_type_perf_data, file_type_record]
self_write_supported_file_types = [file_type_json_compressed, file_type_json,
        file_type_perf_script, file_type_record]

def write_damon_records(records, file_path, file_type, file_permission=None):
    '''Returns None if success, an error string otherwise'''
    if not file_type in self_write_supported_file_types:
        return 'write unsupported file type: %s' % file_type

    if file_type == file_type_json_compressed:
        write_json_compressed(records, file_path)
    elif file_type == file_type_json:
        write_json(records, file_path)
    elif file_type == file_type_perf_script:
        write_perf_script(records, file_path)
    elif file_type == file_type_record:
        write_binary(records, file_path, 2)

    if file_permission != None:
        os.chmod(file_path, file_permission)
    return None

def update_records_file(file_path, file_format, file_permission=None,
        monitoring_intervals=None):
    records, err = parse_records_file(file_path, monitoring_intervals)
    if err:
        return err
    return write_damon_records(records, file_path, file_format,
            file_permission)

# for recording

record_requests = {}
'''
Start recording DAMON's monitoring results using perf.

Returns pipe for the perf.  The pipe should be passed to
stop_monitoring_record() later.
'''
def start_monitoring_record(file_path, file_format, file_permission,
        monitoring_intervals):
    pipe = subprocess.Popen(
            [PERF, 'record', '-a', '-e', PERF_EVENT, '-o', file_path])
    record_requests[pipe] = [file_path, file_format, file_permission,
            monitoring_intervals]
    return pipe

def stop_monitoring_record(perf_pipe):
    file_path, file_format, file_permission = record_requests[perf_pipe][:3]
    monitoring_intervals = record_requests[perf_pipe][3]
    try:
        perf_pipe.send_signal(signal.SIGINT)
        perf_pipe.wait()
    except:
        # perf might already finished
        pass

    if file_format == file_type_perf_data:
        os.chmod(file_path, file_permission)
        return

    err = update_records_file(file_path, file_format, file_permission,
            monitoring_intervals)
    if err != None:
        print('converting format from perf_data to %s failed (%s)' %
                (file_format, err))

# for snapshot

def install_scheme(scheme_to_install):
    '''Install given scheme to all contexts if effectively same scheme is not
    installed.
    Returns whether it found a context doesn't having the scheme, and an error
    if something wrong.
    '''
    installed = False
    kdamonds = _damon.current_kdamonds()
    for kdamond in kdamonds:
        for ctx in kdamond.contexts:
            ctx_has_the_scheme = False
            for scheme in ctx.schemes:
                if scheme.effectively_equal(scheme_to_install, ctx.intervals):
                    ctx_has_the_scheme = True
                    break
            if ctx_has_the_scheme:
                continue
            ctx.schemes.append(scheme_to_install)
            installed = True
    if installed:
        err = _damon.commit(kdamonds)
        if err != None:
            return (False,
                    'committing scheme installed kdamonds failed: %s' % err)
    return installed, None

def tried_regions_to_snapshot(tried_regions, intervals):
    snapshot_end_time_ns = time.time() * 1000000000
    snapshot_start_time_ns = snapshot_end_time_ns - intervals.aggr * 1000
    snapshot = DamonSnapshot(snapshot_start_time_ns, snapshot_end_time_ns)

    for tried_region in tried_regions:
        snapshot.regions.append(tried_region)
    return snapshot

def tried_regions_to_records(monitor_scheme):
    records = []
    for kdamond_idx, kdamond in enumerate(_damon.current_kdamonds()):
        if kdamond.state != 'on':
            continue
        # TODO: Make a cleaner way for passing the index
        for ctx_idx, ctx in enumerate(kdamond.contexts):
            for scheme in ctx.schemes:
                if not scheme.effectively_equal(monitor_scheme, ctx.intervals):
                    continue

                snapshot = tried_regions_to_snapshot(scheme.tried_regions,
                        ctx.intervals)

                records.append(DamonRecord(kdamond_idx, ctx_idx, ctx.intervals,
                    None, None))
                records[-1].snapshots.append(snapshot)
                break
    return records

def get_snapshot_records(access_pattern):
    'return DamonRecord objects each having single DamonSnapshot and an error'
    running_kdamond_idxs = _damon.running_kdamond_idxs()
    if len(running_kdamond_idxs) == 0:
        return None, 'no kdamond running'

    orig_kdamonds = _damon.current_kdamonds()

    monitor_scheme = _damon.Damos(access_pattern=access_pattern)
    installed, err = install_scheme(monitor_scheme)
    if err:
        return None, 'monitoring scheme install failed: %s' % err

    err = _damon.update_schemes_tried_regions(running_kdamond_idxs)
    if err != None:
        if installed:
            err = _damon.commit(orig_kdamonds)
            if err:
                return None, 'monitoring scheme uninstall failed: %s' % err
        return None, 'updating schemes tried regions fail: %s' % err

    records = tried_regions_to_records(monitor_scheme)

    if installed:
        err = _damon.commit(orig_kdamonds)
        if err:
            return records, 'monitoring scheme uninstall failed: %s' % err
    return records, None
