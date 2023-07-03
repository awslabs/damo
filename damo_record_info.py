# SPDX-License-Identifier: GPL-2.0

"""
Print basic information of the access monitoring results record file.
"""

import argparse

import _damo_fmt_str
import _damon_result

class GuideInfo:
    tid = None
    start_time = None
    end_time = None
    lowest_addr = None
    highest_addr = None
    gaps = None

    def __init__(self, tid, start_time):
        self.tid = tid
        self.start_time = start_time
        self.gaps = []

    def regions(self):
        regions = []
        region = [self.lowest_addr]
        for gap in self.gaps:
            for idx, point in enumerate(gap):
                if idx == 0:
                    region.append(point)
                    regions.append(region)
                else:
                    region = [point]
        region.append(self.highest_addr)
        regions.append(region)
        return regions

    def total_space(self):
        ret = 0
        for r in self.regions():
            ret += r[1] - r[0]
        return ret

    def __str__(self):
        lines = ['target_id:%d' % self.tid]
        lines.append('time: %d-%d (%s)' % (self.start_time, self.end_time,
                    _damo_fmt_str.format_time_ns(self.end_time - self.start_time,
                        False)))
        for idx, region in enumerate(self.regions()):
            lines.append('region\t%2d: %020d-%020d (%s)' %
                    (idx, region[0], region[1],
                        _damo_fmt_str.format_sz(region[1] - region[0], False)))
        return '\n'.join(lines)

def is_overlap(region1, region2):
    if region1[1] < region2[0]:
        return False
    if region2[1] < region1[0]:
        return False
    return True

def overlap_region_of(region1, region2):
    return [max(region1[0], region2[0]), min(region1[1], region2[1])]

def overlapping_regions(regions1, regions2):
    overlap_regions = []
    for r1 in regions1:
        for r2 in regions2:
            if is_overlap(r1, r2):
                r1 = overlap_region_of(r1, r2)
        if r1:
            overlap_regions.append(r1)
    return overlap_regions

def get_guide_info(records):
    "return the set of guide information for the moitoring result"
    guides = {}
    for record in records:
        for snapshot in record.snapshots:
            monitor_time = snapshot.end_time
            tid = record.target_id
            if not tid in guides:
                guides[tid] = GuideInfo(tid, monitor_time)
            guide = guides[tid]
            guide.end_time = monitor_time

            last_addr = None
            gaps = []
            for r in snapshot.regions:
                saddr = r.start
                eaddr = r.end

                if not guide.lowest_addr or saddr < guide.lowest_addr:
                    guide.lowest_addr = saddr
                if not guide.highest_addr or eaddr > guide.highest_addr:
                    guide.highest_addr = eaddr

                if not last_addr:
                    last_addr = eaddr
                    continue
                if last_addr != saddr:
                    gaps.append([last_addr, saddr])
                last_addr = eaddr

            if not guide.gaps:
                guide.gaps = gaps
            else:
                guide.gaps = overlapping_regions(guide.gaps, gaps)

    return sorted(list(guides.values()), key=lambda x: x.total_space(),
                    reverse=True)

def pr_guide(records):
    for guide in get_guide_info(records):
        print(guide)

def region_sort_key(region):
    return region[1] - region[0]

def set_argparser(parser):
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    records, err = _damon_result.parse_records_file(args.input)
    if err != None:
        print('monitoring result file (%s) parsing failed (%s)' %
                (args.input, err))
        exit(1)
    pr_guide(records)

if __name__ == '__main__':
    main()
