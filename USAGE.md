This document describes the detailed usage of `damo`.


Prerequisites
=============

Kernel
------

You should first ensure your system is running on a kernel built with at least
``CONFIG_DAMON``, ``CONFIG_DAMON_VADDR``, ``CONFIG_DAMON_PADDR``,
``CONFIG_DAMON_SYSFS``, and ``CONFIG_DAMON_DBGFS``.


Sysfs or Debugfs
----------------

Because `damo` is using the sysfs or debugfs interface of DAMON, you should
ensure at least one of those is mounted.  Note that DAMON debugfs interface is
gonna deprecated in a near future.  Please use sysfs if possible.  If you
depend on DAMON debugfs interface and cannot use sysfs interface, report your
usecase to sj@kernel.org, damon@lists.linux.dev and linux-mm@kvack.org.


Install
-------

You can install `damo` via the official Python packages system, PyPi:

    $ sudo pip3 install damo

Or, you can simply download the source code and make `$PATH` to point the
source code directory.


Overview
========

`damo` provides a subcommands-based interface. Every subcommand provides `-h`
option, which shows the minimal usage of it.


Recording Data Access Pattern
=============================

The ``record`` subcommand records the data access pattern of target workloads
in a file (``./damon.data`` by default).  Note that the file will be owned by
``root`` and have ``600`` permission by default, so only root can read it.  You
can change the permission via ``--output_permission`` option.  You can specify
the monitoring target with 1) the command for execution of the monitoring
target process, 2) pid of running target process, or 3) the special keyword,
`paddr`, if you want to monitor the system's physical memory address space.
Below example shows a command target usage:

    # damo record "sleep 5"

The tool will execute ``sleep 5`` by itself and record the data access patterns
of the process.  Below example shows a pid target usage:

    # sleep 5 &
    # damo record $(pidof sleep)

Finally, the below example shows the use of the special keyword, `paddr`:

    # damo record paddr

In this case, the monitoring target regions defaults to the largest 'System
RAM' region specified in `/proc/iomem` file.  Note that the initial monitoring
target region is maintained rather than dynamically updated like the virtual
memory address spaces monitoring case.

The location of the recorded file can be explicitly set using ``-o`` option.
You can further tune this by setting the monitoring attributes.  To know about
the monitoring attributes in detail, please refer to the DAMON design
[doc](https://damonitor.github.io/doc/html/latest/vm/damon/design.html).

Note that the ``record`` subcommand executes the target command as a root.
Therefore, the user could execute arbitrary commands with root permission.
Hence, sysadmins should allow only trusted users to use ``damo``.  This is the
same as the ``schemes`` subcommand which is mentioned below.  Please take care
of that, either.


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
    base_time_absolute: 8 m 59.809 s

    monitoring_start:                0 ns
    monitoring_end:            104.599 ms
    monitoring_duration:       104.599 ms
    target_id: 18446623438842320000
    nr_regions: 3
    563ebaa00000-563ebc99e000(  31.617 MiB):        1
    7f938d7e1000-7f938ddfc000(   6.105 MiB):        0
    7fff66b0a000-7fff66bb2000( 672.000 KiB):        0

    monitoring_start:          104.599 ms
    monitoring_end:            208.590 ms
    monitoring_duration:       103.991 ms
    target_id: 18446623438842320000
    nr_regions: 4
    563ebaa00000-563ebc99e000(  31.617 MiB):        1
    7f938d7e1000-7f938d9b5000(   1.828 MiB):        0
    7f938d9b5000-7f938ddfc000(   4.277 MiB):        0
    7fff66b0a000-7fff66bb2000( 672.000 KiB):        5

The first line shows the recording started timestamp.  Records of data access
patterns follow.  Each record is separated by a blank line.  Each record first
specifies when the record started (`monitoring_start`) and ended
(`monitoring_end`) relative to the start time, the duration for the recording
(`monitoring_duration`).  Recorded data access patterns of each target follow.
Each data access pattern for each task shows the target's id (``target_id``)
and a number of monitored address regions in this access pattern
(``nr_regions``) first.  After that, each line shows the start/end address,
size, and the number of observed accesses of each region.


heats
-----

The ``raw`` output is very detailed but hard to manually read.  ``heats``
sub-subcommand plots the data in 3-dimensional form, which represents the time
in x-axis, address of regions in y-axis, and the access frequency in z-axis.
Users can optionally set the resolution of the map (``--resol``) and start/end
point of each axis (``--time_range`` and ``--address_range``).  For example:

    $ damo report heats --resol 3 3
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
points.  The three numbers in each line represent time in nanoseconds, address
in bytes and the observed access frequency.

Users can convert this text output into a heatmap image (represents z-axis
values with colors) or other 3D representations using various tools such as
'gnuplot'.  For more convenience, ``heats`` sub-subcommand provides the
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
    target_id:18446623438842320000
    time: 539914032967-596606618651 (56.693 s)
    region   0: 00000094827419009024-00000094827452162048 (31.617 MiB)
    region   1: 00000140271510761472-00000140271717171200 (196.848 MiB)
    region   2: 00000140734916239360-00000140734916927488 (672.000 KiB)

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
    # target_id     18446623438842320000
    # avr:  107.767 MiB
      0             0 B |                                                           |
     25      95.387 MiB |****************************                               |
     50      95.391 MiB |****************************                               |
     75      95.414 MiB |****************************                               |
    100     196.871 MiB |***********************************************************|

Without any option, it shows the distribution of the working set sizes as
above.  It shows 0th, 25th, 50th, 75th, and 100th percentile and the average of
the measured working set sizes in the access pattern records.  In this case,
the working set size was 95.387 MiB for 25th to 75th percentile but 196.871 MiB
in max and 107.767 MiB on average.

By setting the sort key of the percentile using `--sortby`, you can show how
the working set size has chronologically changed.  For example:

    $ ./damo report wss --sortby time
    # <percentile> <wss>
    # target_id     18446623438842320000
    # avr:  107.767 MiB
      0             0 B |                                                           |
     25      95.418 MiB |*****************************                              |
     50     190.766 MiB |***********************************************************|
     75      95.391 MiB |*****************************                              |
    100      95.395 MiB |*****************************                              |

The average is still 107.767 MiB, of course.  And, because the access was
spiked in very short duration and this command plots only 4 data points, we
cannot show when the access spikes made.  Users can specify the resolution of
the distribution (``--range``).  By giving more fine resolution, the short
duration spikes could be more easily found.

Similar to that of ``heats --heatmap``, it also supports 'gnuplot' based simple
visualization of the distribution via ``--plot`` option.


DAMON-based Operation Schemes
=============================

The ``schemes`` subcommand allows users to do DAMON-based memory management
optimizations in a few seconds.  Similar to ``record``, it receives monitoring
attributes and targets.  However, in addition to those, ``schemes`` receive
data access pattern-based memory operation schemes, which describes what memory
operation action should be applied to memory regions showing specific data
access pattern.  Then, it starts the data access monitoring and automatically
applies the schemes to the targets.

The data access pattern can be specified as range of the size, access frequency
rate, and the time that the region has maintained the size and access frequency
rate.  The operations action can be ``willneed``, ``cold``, ``pageout``,
``hugepage`` or ``nohugepage``.  Each of the actions works the same to the
``madvise()`` system call hints having the name.

The data access pattern and the action can be specified using command line
options of the subcommand which having ``--damos_`` prefix.  Please use
``--help`` option for the list of the options.

For example, you can make a running process named 'foo' to use huge pages for
memory regions keeping 2MB or larger size and having very high access frequency
for at least 100 milliseconds using the below commands:

    $ sudo ./damo schemes --damos_sz_region 2M max \
                          --damos_access_rate 90% 100% \
                          --damos_age 100ms max \
                          --damos_action hugepage \
                          $(pidof foo)

The scheme can also specified in json format and passed to the subcommand via
``--schemes`` command line option.  You can pass the json string, or path to a
file containing the json-format scheme specification.  For the json format of
the schemes, you can execute ``damo fmt_json`` with ``--damos_*`` options and
refer to the ``schemes`` part of the output.  This can be useful for more
detailed tuning of the scheme, or for multiple schemes.

NOTE: DAMO used to support one-line scheme specification format before.  The
format is now DEPRECATED, and the support will be removed by 2023-Q2.  Please
report your usage of it to sj@kernel.org, damon@lists.linux.dev, and
linux-mm@kvack.org if you depend on it.
