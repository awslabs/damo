# SPDX-License-Identifier: GPL-2.0

import collections
import copy
import json
import os
import random
import signal
import subprocess
import time
import zlib

import _damo_fmt_str
import _damon

PERF = 'perf'
perf_event_damon_aggregated = 'damon:damon_aggregated'
perf_event_damos_before_apply = 'damon:damos_before_apply'

class DamonSnapshot:
    '''
    Contains a snapshot of data access monitoring results
    '''
    start_time = None
    end_time = None
    regions = None
    total_bytes = None

    def update_total_bytes(self):
        self.total_bytes = sum([r.size() for r in self.regions])

    def __init__(self, start_time, end_time, regions, total_bytes):
        self.start_time = start_time
        self.end_time = end_time
        self.regions = regions
        self.total_bytes = total_bytes
        if self.total_bytes == None:
            self.update_total_bytes()

    @classmethod
    def from_kvpairs(cls, kv):
        return DamonSnapshot(
                _damo_fmt_str.text_to_ns(kv['start_time']),
                _damo_fmt_str.text_to_ns(kv['end_time']),
                [_damon.DamonRegion.from_kvpairs(r) for r in kv['regions']],
                _damo_fmt_str.text_to_bytes(kv['total_bytes'])
                if 'total_bytes' in kv and kv['total_bytes'] != None
                else None)

    def to_kvpairs(self, raw=False):
        return collections.OrderedDict([
            ('start_time', _damo_fmt_str.format_time_ns_exact(
                self.start_time, raw)),
            ('end_time', _damo_fmt_str.format_time_ns_exact(
                self.end_time, raw)),
            ('regions', [r.to_kvpairs() for r in self.regions]),
            ('total_bytes', _damo_fmt_str.format_sz(self.total_bytes, raw)
                if self.total_bytes != None else None),
            ])

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
                    region.nr_accesses.samples, _damon.unit_samples,
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
            snapshots[-1].end_time, new_regions, None)
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

def record_of(target_id, records, intervals):
    for record in records:
        if record.target_id == target_id:
            return record
    record = DamonRecord(None, None, intervals, None, target_id)
    records.append(record)
    return record

def parse_damon_aggregated_perf_script_fields(fields):
    '''
    The line is like below:

    kdamond.0  4452 [000] 82877.315633: damon:damon_aggregated: \
            target_id=18446623435582458880 nr_regions=17 \
            140731667070976-140731668037632: 0 3

    Note that the last field is not in the early version[1].

    [1] https://lore.kernel.org/linux-mm/df8d52f1fb2f353a62ff34dc09fe99e32ca1f63f.1636610337.git.xhao@linux.alibaba.com/
    '''

    if not len(fields) in [9, 10]:
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
    region = _damon.DamonRegion(start_addr, end_addr, nr_accesses,
            _damon.unit_samples, age, _damon.unit_aggr_intervals)

    return region, end_time, target_id, nr_regions

def parse_damos_before_apply_perf_script_fields(fields):
    '''
    The line is like below:

    kdamond.0  4452 [000] 82877.315633: damon:damon_aggregated: \
            target_id=18446623435582458880 nr_regions=17 \
            140731667070976-140731668037632: 0 3

    Note that the last field is not in the early version[1].

    line is like below for damos_before_apply:

    kdamond.0 47293 [000] 80801.060214: damon:damos_before_apply: \
            ctx_idx=0 scheme_idx=0 target_idx=0 nr_regions=11 \
            121932607488-135128711168: 0 136

    [1] https://lore.kernel.org/linux-mm/df8d52f1fb2f353a62ff34dc09fe99e32ca1f63f.1636610337.git.xhao@linux.alibaba.com/
    '''

    if len(fields) != 12:
        return None, None, None, None

    end_time = int(float(fields[3][:-1]) * 1000000000)
    target_id = int(fields[7].split('=')[1])
    nr_regions = int(fields[8].split('=')[1])

    start_addr, end_addr = [int(x) for x in fields[9][:-1].split('-')]
    nr_accesses = int(fields[10])
    age = int(fields[11])
    region = _damon.DamonRegion(start_addr, end_addr, nr_accesses,
            _damon.unit_samples, age, _damon.unit_aggr_intervals)

    return region, end_time, target_id, nr_regions

def parse_perf_script_line(line):
    '''
    line could be that for damon_aggregated or damos_before_apply events
    '''
    fields = line.strip().split()
    if not len(fields) > 5:
        return None, None, None, None
    traceevent = fields[4][:-1]
    if traceevent == perf_event_damon_aggregated:
        return parse_damon_aggregated_perf_script_fields(fields)
    elif traceevent == perf_event_damos_before_apply:
        return parse_damos_before_apply_perf_script_fields(fields)
    else:
        return None, None, None, None

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
            snapshot = DamonSnapshot(start_time, end_time, [], None)
            record.snapshots.append(snapshot)
        snapshot = record.snapshots[-1]
        snapshot.regions.append(region)

        if len(snapshot.regions) == nr_regions:
            snapshot = None

    for record in records:
        for snapshot in record.snapshots:
            snapshot.update_total_bytes()

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
                    [PERF, 'record', '-e', perf_event_damon_aggregated, '--',
                        'sleep', '0'],
                    stderr=subprocess.PIPE)
        except:
            err = 'perf record not working with "%s"' % PERF
    except:
        err = 'perf not found at "%s"' % PERF
    return err

def parse_json(json_str):
    kvpairs = json.loads(json_str)
    return [DamonRecord.from_kvpairs(kvp) for kvp in kvpairs]

def parse_compressed_json(record_file):
    with open(record_file, 'rb') as f:
        compressed = f.read()
    decompressed = zlib.decompress(compressed).decode()
    return parse_json(decompressed)

def parse_json_file(record_file):
    with open(record_file) as f:
        json_str = f.read()
    return parse_json(json_str)

def parse_records_file(record_file, monitoring_intervals=None):
    '''
    Return monitoring results records and error string
    '''

    file_type = subprocess.check_output(
            ['file', '-b', record_file]).decode().strip()
    if file_type == 'JSON data':
        try:
            return parse_json_file(record_file), None
        except Exception as e:
            return None, 'failed parsing json file (%s)' % e
    if file_type == 'zlib compressed data':
        try:
            return parse_compressed_json(record_file), None
        except Exception as e:
            return None, 'failed parsing json compressed file (%s)' % e

    perf_script_output = None
    if file_type == 'ASCII text':
        with open(record_file, 'r') as f:
            perf_script_output = f.read()
    else:
        # might be perf data
        try:
            with open(os.devnull, 'w') as fnull:
                # in some setup, perf record file ends up having no proper
                # ownership.  There's no reason to be strict about that from
                # damo.  As long as we can, just parse it with '--force'
                # option.
                perf_script_output = subprocess.check_output(
                        [PERF, 'script', '--force', '-i', record_file],
                        stderr=fnull).decode()
        except:
            # Should be record format file
            pass
    if perf_script_output != None:
        return parse_perf_script(perf_script_output, monitoring_intervals)
    else:
        return None, 'parsing %s failed' % record_file

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
    having only single snapshot, hence, the reader of the files cannot know the
    start time of the snapshot.  Add a fake snapshot for the case.
    '''

    for record in records:
        snapshots = record.snapshots
        if len(snapshots) != 1:
            continue
        snapshot = snapshots[0]
        snap_duration = snapshot.end_time - snapshot.start_time
        # -1 nr_accesses.samples / -1 age.aggr_intervals means fake
        fake_regions = [_damon.DamonRegion(0, 0,
            -1, _damon.unit_samples, -1, _damon.unit_aggr_intervals)]
        fake_snapshot = DamonSnapshot(snapshot.end_time,
                snapshot.end_time + snap_duration, fake_regions, None)
        snapshots.append(fake_snapshot)

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

file_type_perf_script = 'perf_script'   # perf script output
file_type_perf_data = 'perf_data'       # perf record result file
file_type_json = 'json'                 # list of DamonRecord objects in json
file_type_json_compressed = 'json_compressed'

file_types = [file_type_json_compressed, file_type_json, file_type_perf_script,
        file_type_perf_data]
self_write_supported_file_types = [file_type_json_compressed, file_type_json,
        file_type_perf_script]

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

    if file_permission != None:
        os.chmod(file_path, file_permission)
    return None

def rewrite_record_file(src_file, dst_file, file_format, file_permission=None,
        monitoring_intervals=None):
    records, err = parse_records_file(src_file, monitoring_intervals)
    if err:
        return err
    return write_damon_records(records, dst_file, file_format,
            file_permission)

def update_records_file(file_path, file_format, file_permission=None,
        monitoring_intervals=None):
    return rewrite_record_file(file_path, file_path, file_format,
            file_permission, monitoring_intervals)

# for recording

record_requests = {}
'''
Start recording DAMON's monitoring results using perf.

Returns pipe for the perf.  The pipe should be passed to
stop_monitoring_record() later.
'''
def start_monitoring_record(tracepoint, file_path, file_format,
        file_permission, monitoring_intervals):
    pipe = subprocess.Popen(
            [PERF, 'record', '-a', '-e', tracepoint, '-o', file_path])
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

def find_install_scheme(scheme_to_find):
    '''Install given scheme to all contexts if effectively same scheme is not
    installed.
    Returns whether it found a context doesn't having the scheme, indices list
    for the effectively same schemes, and an error if something wrong.
    '''
    installed = False
    indices = []
    kdamonds = _damon.current_kdamonds()
    for kidx, kdamond in enumerate(kdamonds):
        for cidx, ctx in enumerate(kdamond.contexts):
            ctx_has_the_scheme = False
            for sidx, scheme in enumerate(ctx.schemes):
                if scheme.effectively_equal(scheme_to_find, ctx.intervals):
                    ctx_has_the_scheme = True
                    indices.append([kidx, cidx, sidx])
                    break
            if ctx_has_the_scheme:
                continue
            ctx.schemes.append(scheme_to_find)
            installed = True
            indices.append([kidx, cidx, len(ctx.schemes) - 1])
    if installed:
        err = _damon.commit(kdamonds)
        if err != None:
            return (False, [],
                    'committing scheme installed kdamonds failed: %s' % err)
    return installed, indices, None

def tried_regions_to_snapshot(scheme, intervals, merge_regions):
    snapshot_end_time_ns = time.time() * 1000000000
    snapshot_start_time_ns = snapshot_end_time_ns - intervals.aggr * 1000
    regions = []

    for tried_region in scheme.tried_regions:
        '''Merge regions that having same access pattern, since DAMON usually
        splits regions unnecessarily to keep the min_nr_regions'''
        if merge_regions and len(regions) > 0:
            last_region = regions[-1]
            if (last_region.end == tried_region.start and
                    last_region.nr_accesses == tried_region.nr_accesses and
                    last_region.age == tried_region.age):
                last_region.end = tried_region.end
                continue
        regions.append(tried_region)
    if scheme.tried_bytes != None:
        total_bytes = scheme.tried_bytes
    else:
        total_bytes = None

    return DamonSnapshot(snapshot_start_time_ns, snapshot_end_time_ns, regions,
            total_bytes)

def tried_regions_to_records_of(idxs, merge_regions):
    '''idxs: list of kdamond/context/scheme indices to get records for.  If it
    is None, return records for all schemes'''
    records = []
    for kdamond_idx, kdamond in enumerate(_damon.current_kdamonds()):
        if kdamond.state != 'on':
            continue
        for ctx_idx, ctx in enumerate(kdamond.contexts):
            for scheme_idx, scheme in enumerate(ctx.schemes):
                if not [kdamond_idx, ctx_idx, scheme_idx] in idxs:
                    continue

                snapshot = tried_regions_to_snapshot(scheme, ctx.intervals,
                        merge_regions)

                records.append(DamonRecord(kdamond_idx, ctx_idx, ctx.intervals,
                    scheme_idx, None))
                records[-1].snapshots.append(snapshot)
                break
    return records

def three_regions_of(pid):
    '''
    Return three big mapped virtual address ranges of a given process, which
    separated by the two huge gaps[1].

    [1] https://docs.kernel.org/mm/damon/design.html#vma-based-target-address-range-construction
    '''
    if not os.path.isfile('/proc/%s/maps' % pid):
        print('maps file for %s pid not found' % pid)
        exit(0)
    with open('/proc/%s/maps' % pid, 'r') as f:
        maps_content = f.read()
    regions = []
    for line in maps_content.split('\n'):
        if line == '':
            continue
        start, end = [int(addr, 16) for addr in line.split()[0].split('-')]
        if len(regions) > 0 and regions[-1].end == start:
            regions[-1].end = end
        else:
            regions.append(_damon.DamonRegion(start, end))

    gaps = []
    for idx, region in enumerate(regions):
        if idx == 0:
            continue
        prev_region = regions[idx - 1]
        if region.start != prev_region.end:
            gaps.append([prev_region.end, region.start])
    gaps.sort(key=lambda x: x[1] - x[0], reverse=True)
    if len(gaps) < 2:
        return regions
    # sort biggest two gaps in address
    gaps = sorted(gaps[:2], key=lambda x: x[0])

    return [_damon.DamonRegion(regions[0].start, gaps[0][0]),
            _damon.DamonRegion(gaps[0][1], gaps[1][0]),
            _damon.DamonRegion(gaps[1][1], regions[-1].end)]

def install_target_regions_if_needed(kdamonds):
    '''Returns an error string, or None'''
    need_install = False
    for kd in kdamonds:
        for ctx in kd.contexts:
            if ctx.ops != 'vaddr':
                continue
            need_install = True
            for target in ctx.targets:
                target.regions = three_regions_of(target.pid)
    if not need_install:
        return None
    err = _damon.commit(kdamonds)
    for kd in kdamonds:
        for ctx in kd.contexts:
            if ctx.ops != 'vaddr':
                continue
            for target in ctx.targets:
                target.regions = []
    return err

def update_get_snapshot_records(kdamond_idxs, scheme_idxs,
        total_sz_only, merge_regions):
    if total_sz_only:
        err = _damon.update_schemes_tried_bytes(kdamond_idxs)
        # update_schemes_tried_bytes() can error if the feature is not
        # supported.  Then, full record will be returned
        if err == None:
            records = tried_regions_to_records_of(scheme_idxs, merge_regions)
            return records, None

    err = 'assumed error'
    nr_tries = 0
    while err != None and nr_tries < 5:
        nr_tries += 1

        err = _damon.update_schemes_tried_regions(kdamond_idxs)

        if err != None:
            time.sleep(random.randrange(
                2**(nr_tries - 1), 2**nr_tries) / 100)
    if err != None:
        return None, 'updating schemes tried regions fail: %s' % err

    records = tried_regions_to_records_of(scheme_idxs, merge_regions)
    return records, None

def get_snapshot_records(monitor_scheme, total_sz_only, merge_regions):
    'return DamonRecord objects each having single DamonSnapshot and an error'
    running_kdamond_idxs = _damon.running_kdamond_idxs()
    if len(running_kdamond_idxs) == 0:
        return None, 'no kdamond running'

    orig_kdamonds = _damon.current_kdamonds()

    err = install_target_regions_if_needed(orig_kdamonds)
    if err != None:
        return None, 'vaddr region install failed (%s)' % err

    installed, idxs, err = find_install_scheme(monitor_scheme)
    if err:
        return None, 'monitoring scheme install failed: %s' % err

    records, err = update_get_snapshot_records(running_kdamond_idxs, idxs,
            total_sz_only, merge_regions)

    if installed:
        uninstall_err = _damon.commit(orig_kdamonds)
        if uninstall_err:
            errmsg = 'monitoring scheme uninstall failed: %s' % uninstall_err
            if err != None:
                err += ', %s' % errmsg
            else:
                err = errmsg

    return records, err

def get_snapshot_records_for_schemes(idxs, total_sz_only, merge_regions):
    '''idxs: list of kdamond/context/scheme indices to get records for.
    Return DamonRecord objects each having single DamonSnapshot and an error'''
    running_kdamond_idxs = _damon.running_kdamond_idxs()
    if len(running_kdamond_idxs) == 0:
        return None, 'no kdamond running'

    return update_get_snapshot_records(running_kdamond_idxs, idxs,
            total_sz_only, merge_regions, None)

def filter_by_pattern(record, access_pattern):
    sz_bytes = access_pattern.sz_bytes
    nr_acc = access_pattern.nr_acc_min_max
    age = access_pattern.age_min_max

    for snapshot in record.snapshots:
        filtered = []
        for region in snapshot.regions:
            sz = region.size()
            if sz < sz_bytes[0] or sz_bytes[1] < sz:
                continue
            intervals = record.intervals
            if intervals == None:
                filtered.append(region)
                continue
            region.nr_accesses.add_unset_unit(intervals)
            freq = region.nr_accesses.percent
            if freq < nr_acc[0].percent or nr_acc[1].percent < freq:
                continue
            region.age.add_unset_unit(intervals)
            usecs = region.age.usec
            if usecs < age[0].usec or age[1].usec < usecs:
                continue
            filtered.append(region)
        snapshot.regions = filtered

def filter_by_addr(region, addr_ranges):
    regions = []
    for start, end in addr_ranges:
        # out of the range
        if region.end <= start or end <= region.start:
            continue
        # in the range
        if start <= region.start and region.end <= end:
            regions.append(copy.deepcopy(region))
            continue
        # overlap
        copied = copy.deepcopy(region)
        copied.start = max(start, region.start)
        copied.end = min(end, region.end)
        regions.append(copied)
    return regions

def filter_records_by_addr(records, addr_ranges):
    for record in records:
        for snapshot in record.snapshots:
            filtered_regions = []
            for region in snapshot.regions:
                filtered_regions += filter_by_addr(region, addr_ranges)
            snapshot.regions = filtered_regions
            snapshot.update_total_bytes()

def get_snapshot_records_of(request):
    '''
    get records containing single snapshot from running kdamonds
    '''
    if request.tried_regions_of == None:
        filters = []
        if request.address_ranges and _damon.feature_supported('schemes_filters_addr'):
            for start, end in request.address_ranges:
                filters.append(_damon.DamosFilter('addr', False,
                    address_range=_damon.DamonRegion(start, end)))

        monitor_scheme = _damon.Damos(access_pattern=request.access_pattern,
                filters=filters)

        records, err = get_snapshot_records(monitor_scheme,
                request.total_sz_only, not request.dont_merge_regions)
    else:
         records, err = get_snapshot_records_for_schemes(
                 request.tried_regions_of, request.total_sz_only,
                 not request.dont_merge_regions)
    return records, err

class RecordGetRequest:
    # TODO: Extend to be used for recording

    # source of the record.  If both are None, get snapshot
    tried_regions_of = None
    record_file = None

    # filters of the record
    access_pattern = None
    address_ranges = None

    # more detailed requests
    total_sz_only = None
    dont_merge_regions = None

    def __init__(self, tried_regions_of, record_file, access_pattern,
            address_ranges, total_sz_only, dont_merge_regions):
        self.tried_regions_of = tried_regions_of
        self.record_file = record_file
        self.access_pattern = access_pattern
        self.address_ranges = address_ranges
        self.total_sz_only = total_sz_only
        self.dont_merge_regions = dont_merge_regions

def get_records(request):
    if request.record_file == None:
        records, err = get_snapshot_records_of(request)
        if err != None:
            return None, err
        if _damon.feature_supported('schemes_filters_addr'):
            # get_snapshot_records_of() has already handled address filter
            return records, None
    else:
        if not os.path.isfile(request.record_file):
            return None, '%s not found' % input_file

        records, err = parse_records_file(request.record_file)
        if err:
            return None, ('parsing %s failed (%s)' %
                    (request.record_file, err))
        for record in records:
            filter_by_pattern(record, request.access_pattern)

    if request.address_ranges:
        filter_records_by_addr(records, request.address_ranges)
    return records, None
