This document describes detailed usage of `damo`.  The tool provides a
subcommands based interface. Every subcommand provides -h option, which
provides the minimal usage of it. Currently, the tool supports two subcommands,
record and report.

Below example commands assume you set $PATH to point tools/damon/ of the
development tree for brevity. It is not mandatory for use of damo, though.


Recording Data Access Pattern
=============================

The ``record`` subcommand records the data access pattern of target workloads
in a file (``./damon.data`` by default).  Note that the file will owned by
``root`` but have ``644`` permission, so anyone could read it.  You can specify
the target with 1) the command for execution of the monitoring target process,
2) pid of running target process, or 3) the special keyword, 'paddr', if you
want to monitor the system's physical memory address space.  Below example
shows a command target usage:

    # cd <kernel>/tools/damon/
    # damo record "sleep 5"

The tool will execute ``sleep 5`` by itself and record the data access patterns
of the process.  Below example shows a pid target usage:

    # sleep 5 &
    # damo record `pidof sleep`

Finally, below example shows the use of the special keyword, 'paddr':

    # damo record paddr

In this case, the monitoring target regions defaults to the largetst 'System
RAM' region specified in '/proc/iomem' file.  Note that the initial monitoring
target region is maintained rather than dynamically updated like the virtual
memory address spaces monitoring case.

The location of the recorded file can be explicitly set using ``-o`` option.
You can further tune this by setting the monitoring attributes.  To know about
the monitoring attributes in detail, please refer to the
:doc:`/vm/damon/design`.

Note that the ``record`` subcommand executes the target command as a root.
Therefore, the user could execute arbitrary commands with root permission.
Hence, sysadmins should allow only trusted users to use ``damo``.  This is same
to ``schemes`` subcommand that mentioned below.  Please take care for that,
either.


Analyzing Data Access Pattern
=============================

The ``report`` subcommand reads a data access pattern record file (if not
explicitly specified using ``-i`` option, reads ``./damon.data`` file by
default) and generates human-readable reports.  You can specify what type of
report you want using a sub-subcommand to ``report`` subcommand.  ``raw``,
``heats``, and ``wss`` report types are supported for now.


raw
---

``raw`` sub-subcommand simply transforms the binary record into a
human-readable text.  For example:

    $ damo report raw
    start_time:  193485829398
    rel time:                0
    nr_tasks:  1
    target_id:  1348
    nr_regions:  4
    560189609000-56018abce000(  22827008):  0
    7fbdff59a000-7fbdffaf1a00(   5601792):  0
    7fbdffaf1a00-7fbdffbb5000(    800256):  1
    7ffea0dc0000-7ffea0dfd000(    249856):  0

    rel time:        100000731
    nr_tasks:  1
    target_id:  1348
    nr_regions:  6
    560189609000-56018abce000(  22827008):  0
    7fbdff59a000-7fbdff8ce933(   3361075):  0
    7fbdff8ce933-7fbdffaf1a00(   2240717):  1
    7fbdffaf1a00-7fbdffb66d99(    480153):  0
    7fbdffb66d99-7fbdffbb5000(    320103):  1
    7ffea0dc0000-7ffea0dfd000(    249856):  0

The first line shows the recording started timestamp (nanosecond).  Records of
data access patterns follows.  Each record is separated by a blank line.  Each
record first specifies the recorded time (``rel time``) in relative to the
start time, the number of monitored tasks in this record (``nr_tasks``).
Recorded data access patterns of each task follow.  Each data access pattern
for each task shows the target's pid (``target_id``) and a number of monitored
address regions in this access pattern (``nr_regions``) first.  After that,
each line shows the start/end address, size, and the number of observed
accesses of each region.


heats
-----

The ``raw`` output is very detailed but hard to manually read.  ``heats``
sub-subcommand plots the data in 3-dimensional form, which represents the time
in x-axis, address of regions in y-axis, and the access frequency in z-axis.
Users can set the resolution of the map (``--tres`` and ``--ares``) and
start/end point of each axis (``--tmin``, ``--tmax``, ``--amin``, and
``--amax``) via optional arguments.  For example:

    $ damo report heats --tres 3 --ares 3
    0               0               0.0
    0               7609002         0.0
    0               15218004        0.0
    66112620851     0               0.0
    66112620851     7609002         0.0
    66112620851     15218004        0.0
    132225241702    0               0.0
    132225241702    7609002         0.0
    132225241702    15218004        0.0

This command shows a recorded access pattern in heatmap of 3x3 resolution.
Therefore it shows 9 data points in total.  Each line shows each of the data
points.  The three numbers in each line represent time in nanosecond, address,
and the observed access frequency.

Users will be able to convert this text output into a heatmap image (represents
z-axis values with colors) or other 3D representations using various tools such
as 'gnuplot'.  For more convenience, ``heats`` sub-subcommand provides the
'gnuplot' based heatmap image creation.  For this, you can use ``--heatmap``
option.  Also, note that because it uses 'gnuplot' internally, it will fail if
'gnuplot' is not installed on your system.  For example:

    $ ./damo report heats --heatmap heatmap.png

Creates the heatmap image in ``heatmap.png`` file.  It supports ``pdf``,
``png``, ``jpeg``, and ``svg``.

If the target address space is virtual memory address space and you plot the
entire address space, the huge unmapped regions will make the picture looks
only black.  Therefore you should do proper zoom in / zoom out using the
resolution and axis boundary-setting arguments.  To make this effort minimal,
you can use ``--guide`` option as below:

    $ ./damo report heats --guide
    target_id:1348
    time: 193485829398-198337863555 (4852034157)
    region   0: 00000094564599762944-00000094564622589952 (22827008)
    region   1: 00000140454009610240-00000140454016012288 (6402048)
    region   2: 00000140731597193216-00000140731597443072 (249856)

The output shows unions of monitored regions (start and end addresses in byte)
and the union of monitored time duration (start and end time in nanoseconds) of
each target task.  Therefore, it would be wise to plot the data points in each
union.  If no axis boundary option is given, it will automatically find the
biggest union in ``--guide`` output and set the boundary in it.


wss
---

The ``wss`` type extracts the distribution and chronological working set size
changes from the records.  For example:

    $ ./damo report wss
    # <percentile> <wss>
    # target_id   1348
    # avr:  66228
    0       0
    25      0
    50      0
    75      0
    100     1920615

Without any option, it shows the distribution of the working set sizes as
above.  It shows 0th, 25th, 50th, 75th, and 100th percentile and the average of
the measured working set sizes in the access pattern records.  In this case,
the working set size was zero for 75th percentile but 1,920,615 bytes in max
and 66,228 bytes on average.

By setting the sort key of the percentile using '--sortby', you can show how
the working set size has chronologically changed.  For example:

    $ ./damo report wss --sortby time
    # <percentile> <wss>
    # target_id   1348
    # avr:  66228
    0       0
    25      0
    50      0
    75      0
    100     0

The average is still 66,228.  And, because the access was spiked in very short
duration and this command plots only 4 data points, we cannot show when the
access spikes made.  Users can specify the resolution of the distribution
(``--range``).  By giving more fine resolution, the short duration spikes could
be found.

Similar to that of ``heats --heatmap``, it also supports 'gnuplot' based simple
visualization of the distribution via ``--plot`` option.


DAMON-based Operation Schemes
=============================

The ``schemes`` subcommand allows users to do DAMON-based memory management
optimizations in a few seconds.  Similar to ``record``, it receives monitoring
attributes and target.  However, in addition to those, ``schemes`` receives
data access pattern-based memory operation schemes, which describes what memory
operation action should be applied to memory regions showing specific data
access pattern.  Then, it starts the data access monitoring and automatically
applies the schemes to the targets.

The operation schemes should be saved in a text file in below format and passed
to ``schemes`` subcommand via ``--schemes`` option.

    min-size max-size min-acc max-acc min-age max-age action

The format also supports comments, several units for size and age of regions,
and human readable action names.  Currently supported operation actions are
``willneed``, ``cold``, ``pageout``, ``hugepage`` and ``nohugepage``.  Each of
the actions works same to the madvise() system call hints having the name.
Please also note that the range is inclusive (closed interval), and ``0`` for
max values means infinite. Below example schemes are possible.

    # format is:
    # <min/max size> <min/max frequency (0-100)> <min/max age> <action>
    #
    # B/K/M/G/T for Bytes/KiB/MiB/GiB/TiB
    # us/ms/s/m/h/d for micro-seconds/milli-seconds/seconds/minutes/hours/days
    # 'min/max' for possible min/max value.

    # if a region keeps a high access frequency for >=100ms, put the region on
    # the head of the LRU list (call madvise() with MADV_WILLNEED).
    min    max      80      max     100ms   max willneed

    # if a region keeps a low access frequency for >=200ms and <=one hour, put
    # the region on the tail of the LRU list (call madvise() with MADV_COLD).
    min     max     10      20      200ms   1h  cold

    # if a region keeps a very low access frequency for >=60 seconds, swap out
    # the region immediately (call madvise() with MADV_PAGEOUT).
    min     max     0       10      60s     max pageout

    # if a region of a size >=2MiB keeps a very high access frequency for
    # >=100ms, let the region to use huge pages (call madvise() with
    # MADV_HUGEPAGE).
    2M      max     90      100     100ms   max hugepage

    # If a regions of a size >=2MiB keeps small access frequency for >=100ms,
    # avoid the region using huge pages (call madvise() with MADV_NOHUGEPAGE).
    2M      max     0       25      100ms   max nohugepage

For example, you can make a running process named 'foo' to use huge pages for
memory regions keeping 2MB or larger size and having very high access frequency
for at least 100 milliseconds using below commands:

    $ echo "2M max    90 max    100ms max    hugepage" > my_thp_scheme
    $ ./damo schemes --schemes my_thp_scheme `pidof foo`
