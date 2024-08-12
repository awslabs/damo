This document describes the detailed usage of `damo`.  This doesn't cover all
details of `damo` but only major features.  This document may not complete and
up to date sometimes.  Please don't hesitate at asking questions and
improvement of this document via GitHub
[issues](https://github.com/damonitor/damo/issues) or
[mails](https://lore.kernel.org/damon).


Prerequisites
=============

Kernel
------

You should first ensure your system is running on a kernel built with at least
``CONFIG_DAMON``, ``CONFIG_DAMON_VADDR``, ``CONFIG_DAMON_PADDR``, and
``CONFIG_DAMON_SYSFS``.  Depending on the kernel version, you may need to
enable ``CONFIG_DAMON_DBGFS`` instead of ``CONFIG_DAMON_SYSFS``.

Sysfs or Debugfs
----------------

Because `damo` is using the sysfs or debugfs interface of DAMON, you should
ensure at least one of those is mounted.  Note that DAMON debugfs interface is
deprecated.  Please use sysfs.  If you depend on DAMON debugfs interface and
cannot use sysfs interface, [report](REPORTING.md) your usecase to the
community.

Perf
----

`damo` uses `perf`[1] for recording DAMON's access monitoring results.  Please
ensure your system is having it if you will need to do record DAMON's
monitoring results.  If you will not do the recording, you don't need to
install `perf` on your system, though.

[1] https://perf.wiki.kernel.org/index.php/Main_Page

Basic Concepts of DAMON
-----------------------

`damo` is a user space tool for `DAMON`.  Hence, for advanced and optimized use
of `damo` rather than simple "Getting Started" tutorial, you should first
understand the concepts of DAMON.  There are a number of links to resources
including DAMON introduction talks and publications at the project
[site](https://damonitor.github.io).  The official design
[document](https://docs.kernel.org/mm/damon/design.html) is recommended among
those, since we will try to keep it up to date always, and appropriate for
DAMON users.

Install
=======

You can install `damo` via the official Python packages system, PyPi:

    $ sudo pip3 install damo

Or, you can use your distribution's package manager if available.  Refer to
below [repology](https://repology.org/project/damo) data to show the packaging
status of `damo` for each distribution.

[![Packaging status](https://repology.org/badge/vertical-allrepos/damo.svg)](https://repology.org/project/damo/versions)

If none of above options work for you, you can simply download the source code
and use `damo` file at the root of the source tree.  Optionally, you could add
the path to the source code directory to your `$PATH`.

Overview
========

`damo` provides a subcommands-based interface.  You can show the list of the
available commands and brief description of those via `damo --help`.  The major
commands can be categorized as below:

- For controlling DAMON (monitoring and monitoring-based system optimization)
  - `start`, `tune`, and `stop` are included
- For snapshot and visualization of DAMON's monitoring results and running
  status
  - `show`, and `status` are included
- For recording the access monitoring results and utilizing the records
  - `record`, `report` and `replay` are included
- For more convenient use of `damo`
  - `version` and `fmt_json` are included

Every subcommand also provides `--help` option, which shows the basic usage of
it.  Below sections introduce more details about the major subcommands.

Note that some of the subcommands that not described in this document would be
in experimental stage, or not assumed to be used in major use cases.  Those
could be deprecated and removed without any notice and grace periods.

DAMON Control (Access Monitoring and Monitoring-based System Optimization)
==========================================================================

The main purposes of `damo` is operating DAMON, as the name says (DAMO: Data
Access Monitor Operator).  In other words, `damo` is for helping control of
DAMON and retrieval/interpretation of the results.

`damo start`
------------

`damo start` starts DAMON as users request.  Specifically, users can specify
how and to what address spaces DAMON should do monitor accesses, and what
access monitoring-based system optimization to do.  The request can be made via
several command line options of the command.  You can get the full list of the
options via `damo start --help`.

The command exits immediately after starting DAMON as requested.  It exits with
exit value `0` if it successfully started DAMON.  Otherwise, the exit value
will be non-zero.

### Simple Target Argument

The command receives one positional argument called deducible target.  It could
be used for specifying monitoring target, or full DAMON parameters.  The
command will try to deduce the type of the argument value and use it.

With the argument, users can specify the monitoring target with 1) the command
for execution of the monitoring target process, 2) pid of running target
process, or 3) the special keyword, `paddr`, if you want to monitor the
system's physical memory address space.

Below example shows a command target usage:

    # damo start "sleep 5"

The command will execute ``sleep 5`` by itself and start monitoring the data
access patterns of the process.

Note that the command requires root permission, and hence executes the
monitoring target command as a root.  This means that the user could execute
arbitrary commands with root permission.  Hence, sysadmins should allow only
trusted users to use ``damo``.

Below example shows a pid target usage:

    # sleep 5 &
    # damo start $(pidof sleep)

Finally, below example shows the use of the special keyword, `paddr`:

    # damo start paddr

In this case, the monitoring target regions defaults to the largest 'System
RAM' region specified in `/proc/iomem` file.  Note that the initial monitoring
target region is maintained rather than dynamically updated like the virtual
memory address spaces monitoring case.

Users can specify full DAMON parameters at once.  Refer to "Full DAMON
Parameters Update" [section](#full-damon-parameters-update) below for the
detail of the concept, and "`damo fmt_json`" [section](#damo-fmt_json) below
for the format of the input.

### Partial DAMON Parameters Update

The command line options basically support specification of partial DAMON
parameters such as monitoring intervals and DAMOS action.  With a good
understanding of DAMON's core concepts, understanding what each of such options
mean with their brief description on the help message wouldn't be that
difficult.

Note that these command line options support only single kdamond, single DAMON
context, and single monitoring target case at the moment.  Users can make
requests without such limitation using full DAMON parameters input.  Refer to
'Full DAMON Parameters Update' [section](#full-damon-parameters-update) below
for the detail.

### Partial DAMOS Parameters Update

Command line options having prefix of `--damos_` are for DAMON-based operation
schemes.  Those options are allowed to be specified multiple times for
requesting multiple schemes.  For example, below shows how you can start DAMON
with two DAMOS schemes, one for proactive LRU-prioritization of hot pages and
the other one for proactive LRU-deprioritization of cold pages.

    # damo start \
        --damos_action lru_prio --damos_access_rate 50% max --damos_age 5s max \
        --damos_action lru_deprio --damos_access_rate 0% 0% --damos_age 5s max

This command will ask DAMON to find memory regions that showing >=50% access
rate for >=5 seconds and prioritize the pages of the regions on the Linux
kernel's LRU lists, while finding memory regions that not accessed for >=5
seconds and deprioritizes the pages of the regions from the LRU lists.

### Full DAMON Parameters Update

As mentioned above, the partial DAMON parameters update command line options
support only single kdamond and single DAMON context.  That should be enough
for many use cases, but for system-wide dynamic DAMON usages, that could be
restrictive.  Also, specifying each parameter that different from their default
values could be not convenient.  Users may want to specify full parameters at
once in such cases.  For such users, the command supports `--kdamonds` option.
It receives a specification of kdamonds that would contains all DAMON
parameters in `json` or `yaml` format.  Either a string of the format, or a
path to a file containing the string can be passed to the option.  Then, `damo`
starts DAMON with the specification.

For the full DAMON parameters input format, please refer to `damo fmt_json`
[documentation](#damo-fmt_json) below, or simply try the command.  The
`--kdamonds` option keyword can also simply omitted because the full DAMON
parameters input can used as is for the `deducible target` (refer to "Simple
Target Argument" [section](#simple-target-argument) above).

Note that multiple DAMON contexts per kdamond is not supported as of
2023-09-12, though.

### Full DAMOS Parameters Update

The Partial DAMOS parameters update options support multiple schemes as abovely
mentioned.  However, it could be still too manual in some cases and users may
want to provide all inputs at once.  For such cases, `--schemes` option
receives a json-format specification of DAMOS schemes.  The format is same to
schemes part of the `--kdamonds` input.

You could get some example json format input for `--schemes` option from
any `.json` files in `damon-tests`
[repo](https://github.com/damonitor/damon-tests/tree/next/perf/schemes).

`damo tune`
-----------

`damo tune` updates the DAMON parameters while DAMON is running.  It provides
the set of command line options that same to that of `damo start`.  Note that
users should provide the full request specification to this command.  If only a
partial parameters are specified via the command line options of this command,
unspecified parameters of running DAMON will be updated to their default
values.

The command exits immediately after updating DAMON parameters as requested.  It
exits with exit value `0` if the update succeeded.  Otherwise, the exit value
will be non-zero.

`damo stop`
-----------

`damo stop` stops the running DAMON.

The command exits immediately after stopping DAMON.  It exits with exit value
`0` if it successfully terminated DAMON.  Otherwise, the exit value will be
non-zero.

Snapshot and Visualization of DAMON Monitoring Results and Running Status
=========================================================================

`damo show`
-----------

`damo show` takes a snapshot of running DAMON's monitoring results and show it.

For example:

    # damo start
    # damo show
    0   addr [4.000 GiB   , 16.245 GiB ) (12.245 GiB ) access 0 %   age 7 m 32.100 s
    1   addr [16.245 GiB  , 28.529 GiB ) (12.284 GiB ) access 0 %   age 12 m 40.500 s
    2   addr [28.529 GiB  , 40.800 GiB ) (12.271 GiB ) access 0 %   age 15 m 10.100 s
    3   addr [40.800 GiB  , 52.866 GiB ) (12.066 GiB ) access 0 %   age 15 m 58.600 s
    4   addr [52.866 GiB  , 65.121 GiB ) (12.255 GiB ) access 0 %   age 16 m 15.900 s
    5   addr [65.121 GiB  , 77.312 GiB ) (12.191 GiB ) access 0 %   age 16 m 22.400 s
    6   addr [77.312 GiB  , 89.537 GiB ) (12.225 GiB ) access 0 %   age 16 m 24.200 s
    7   addr [89.537 GiB  , 101.824 GiB) (12.287 GiB ) access 0 %   age 16 m 25 s
    8   addr [101.824 GiB , 126.938 GiB) (25.114 GiB ) access 0 %   age 16 m 25.300 s
    total size: 122.938 GiB

### DAMON Monitoring Results Structure

The biggest unit of the monitoring result is called 'record'.  Each record
contains monitoring results snapshot that retrieved for each
kdamond/context/target combination.  Hence, the number of records that `damo
show` will show depends on how many kdamond/context/target combination exists.

Each record contains multiple snapshots of the monitoring results that
retrieved for each `aggregation interval`.  For `damo show`, therefore, each
record will contain only one single snapshot.

Each snapshot contains regions information.  Each region information contains
the monitoring results for the region including the start and end addresses of
the memory region, `nr_accesses`, and `age`.  The number of regions per
snapshot would depend on the `min_nr_regions` and `max_nr_regions` DAMON
parameters, and actual data access pattern of the monitoring target address
space.

### `damo`'s way of showing DAMON Monitoring Results

`damo show` shows the information in an enclosed hierarchical way like below:

    <record 0 head>
        <snapshot 0 head>
            <region 0 information>
            [...]
        <snapshot 0 tail>
        [...]
     <record 0 tail>
     [...]

That is, information of record and snapshot can be
shown twice, once at the beginning (before showing it's internal data), and
once at the end.  Meanwhile, the information of regions can be shown only once
since it is the lowest level that not encloses anything.  By default, record
and snapshot head/tail are skipped if there is only one record and one
snapshot.  That's why above `damo show` example output shows only regions
information.

### Customization of The Output

Users can customize what information to be shown in which way for the each
position using `--format_{record,snapshot,region}[_{head,tail}]` option.  Each
of the option receives a string for the template.  The template can have any words and
special format keywords for each position.  For example, `<start address>`, `<end
address>`, `<access rate>`, or `<age>` keywords are available for
`--foramt_region` option's value.  The template can also have arbitrary
strings.  The newline character (`\n`) is also supported.  Each of the keywords
for each position and their brief description can be shown via
`--ls_{record,snapshot,region}_format_keywords` option.  Actually, `damo show`
also internally uses the customization feature with its default templates.

For example:

    # damo start
    # damo show --format_region "region that starts from <start address> and ends at <end address> was having <access rate> access rate for <age>."
    region that starts from 4.000 GiB    and ends at 16.251 GiB  was having 0 %   access rate for 40.700 s.
    region that starts from 16.251 GiB   and ends at 126.938 GiB was having 0 %   access rate for 47.300 s.
    total size: 122.938 GiB

#### Region Visualization via Boxes

For region information customization, a special keyword called `<box>` is
provided.  It represents each region's access pattern with its shape and color.
By default it represents each region's relative age, access rate
(`nr_accesses`), and size with its length, color, and height, respectively.
That is, `damo show --format_region "<box>"` shows visualization of the access
pattern, by showing location of each region in Y-axis, the hotness with color
of each box, and how long the hotness has continued in X-axis.  Showing only
the first column of the output would be somewhat similar to an access heatmap
of the target address space.

For convenient use of it with a default format, `damo show` provides
`--region_box` option.  Output of the command with the option would help users
better to understand.

Users can further customize the box using `damo show` options that having
`--region_box_` prefix.  For example, users can set what access information to
be represented by the length, color, and height, and whether the values should
be represented in logscale or linearscale.

#### Sorting and Filtering Regions Based on Access Pattern

By default, `damo show` shows all regions that sorted by their start address.
Different users would have different interest to regions having specific access
pattern.  Someone would be interested in hot and small regions, while some
others are interested in cold and big regions.

For such cases, users can make it to sort regions with specific access pattern
values as keys including `access_rate`, `age`, and `size` via
`--sort_regions_by` option.  `--sort_regions_dsc` option can be used to do
desscending order sorting.

Further, users can make `damo show` to show only regions of specific access
pattern and address ranges using options including `--sz_region`,
`--access_rate`, `--age`, and `--address`.  Note that the filtering could
reduce DAMON's overhead, and therefore recommended to be used if you don't need
full results and your system is sensitive to any resource waste.

#### Sorting Regions Based on Hotness

Note: This is an experimental feature at the moment.  Some changes could be
made, or the support can be dropped in future.

Users can sort the regions based on hotness of the regions by providing
'temperature' as the sort key (`--sort_regions_by`).

The hotness is calculated as weighted sum of the access pattern values (`size`,
`access_rate`, and `age`).  If `access_rate` is zero, the hotness becomes the
weighted sum multiplies `-1`.  By default, the weights for the three values are
0, 100, and 100, respectively.  Users can set custom weights using
`--temperature_weights` option.

For example:

    $ sudo damo show --style simple-boxes --sort_regions_by temperature
    |0000000000000000000000000000000000000000| size 36.488 MiB  access rate 0 %   age 42.300 s
     |000000000000000000000000000000000000000| size 4.000 KiB   access rate 0 %   age 42 s
     |000000000000000000000000000000000000000| size 18.367 MiB  access rate 0 %   age 32.800 s
      |00000000000000000000000000000000000000| size 11.234 MiB  access rate 0 %   age 21.300 s
       |0000000000000000000000000000000000000| size 18.219 MiB  access rate 0 %   age 14.300 s
        |000000000000000000000000000000000000| size 17.859 MiB  access rate 0 %   age 7.400 s
                                           |3| size 8.000 KiB   access rate 35 %  age 0 ns
              |555555555555555555555555555555| size 8.000 KiB   access rate 65 %  age 500 ms
           |999999999999999999999999999999999| size 9.535 MiB   access rate 100 % age 2.300 s

`damo status`
-------------

`damo status` shows the status of DAMON.  It shows every kdamond with the
parameters that applied to it, running status (`on` or `off`), and DAMOS
schemes status including their statistics and detailed applied regions
information.

Note that users can use `--json` to represent the status in a json format.  And
the json format output can again be used for `--kdamonds` or the positional
option of some DAMON control commands including `damo start` and `damo tune`.

The command exits immediately after showing the current status.  It exits with
exit value `0` if it successfully retrieved and shown the status of DAMON.
Otherwise, the exit value will be non-zero.

For recording the access monitoring results and visualizing those
=================================================================

`damo show` shows only a snapshot.  Since it contains the `age` of each region,
it can be useful enough for online profiling or debugging.  For detailed
offline profiling or debugging, though, recording every changing monitoring
results and analyzing the record could be more helpful.  In this case, the
`record` would same to that for `damo show`, but simply contains multiple
`snapshot`s.

`damo record` (Recording Data Access Pattern)
---------------------------------------------

`damo record` records the data access pattern of target workloads in a file
(`./damon.data` by default).  The path to the file can be set with `--out`
option.  The command requires root permission.  The output file will be owned
by `root` and have `600` permission by default, so only root can read it.
Users can change the permission via `--output_permission` option.

Other than the two options, `damo record` receives command line options that
same to those for `damo start` and `damo tune`.  If DAMON is already running,
users can simply record the monitoring results of the running DAMON by
providing no DAMON parameter options.  For example, below will start DAMON for
physical address space monitoring, record the monitoring results, and save the
records in `damon.data` file.

    # damo start
    # damo record

Or, users can ask `damo record` to start DAMON by themselves, together with the
monitoring target command, like below:

    # damo record "sleep 5"

or, for already running process, like below:

    # damo record $(pidof my_workload)

### Recording Profile Information

Note: This feature is an experimental one.  Some changes could be made, or the
support can be dropped in future.

`damo record` commands records record profiling information of the system
together with the access pattern.  Internally, it runs `perf record` while
`damo record` is running, and store the `perf` output as a file of name same to
the access pattern record file (specified by `--out` option of `damo record`)
except having `.profile` suffix.  Hence, `damon.data.profile` is the default
name of the profile information.

Because the profile information record file is simply `perf record` output,
users can further analyze the profile information using `perf` or any `perf
record` output compatible tools.

### Recording Memory Footprints

Note: This is an experimental feature at the moment.  Some changes could be
made, or the support can be dropped in future.

`damo record` command records memory usage information of the record target
processes and the system together with the access pattern.  Internally, it
parses `/proc/meminfo` and `/proc/<pid>/statm` files for the monitoring target
processes, and save the results as a json file of the name same to the access
pattern record file (specified by `--out` option of `damo record`) except
having `.mem_footprint` suffix.  Hence, `damon.data.mem_footprint` is the
default name of the profile information.

Users could use the files for vaious purpose.  For an example, users could find
when how much memory is allocated by the process and really accessed, by
comparing the recorded residential set size and DAMON-based working set size.
[`damo report footprints`](#footprints) and [`damo report wss`](#wss) could be
used for the purpose.

### Recording Memory Mappings

Note: This is an experimental feature at the moment.  Some changes could be
made, or the support can be dropped in future.

`damo record` command records virtual memory mapping information of the record
target processes.  Internally, it parses `/proc/<pid>/maps` files of the
monitoring target processes, and save the results as a json file of the name
same to the access pattern record file (specified by `--out` option of `damo
record`) except having `.vmas` suffix.  Hence, `damon.data.vmas` is the default
name of the memory mapping information.

### Recording CPU Usages

Note: This is an experimental feature at the moment.  Some changes could be
made, or the support can be dropped in future.

`damo record` command records CPU usages of monitoring target processes and
kdamonds by default.  The record data is saved as a json file of the name same
to the access pattern record file (specified by `--out` option of `damo
record`) except having `.proc_stats` suffix.  Hence, `damon.data.proc_stats` is
the default name of the CPU usage information.

`damo report` (Visualizing Recorded Data Access Pattern)
--------------------------------------------------------

`damo report` reads a data access pattern record file (if not explicitly
specified using ``-i`` option, reads ``./damon.data`` file by default) and
generates human-readable reports.  Users can specify what type of report they
want using a sub-subcommand to `damo report`.  `raw`, `heats`, and `wss` report
types are supported.

### raw

`raw` sub-subcommand directly transforms the binary record into a
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

The first line shows the recording started timestamp (`base_time_absolute`).
Records of data access patterns follow.  Each record is separated by a blank
line.  Each record first specifies when the record started (`monitoring_start`)
and ended (`monitoring_end`) relative to the start time, the duration for the
recording (`monitoring_duration`).  Recorded data access patterns of each
target follow.  Each data access pattern for each task shows the target's id
(``target_id``) and a number of monitored address regions in this access
pattern (``nr_regions``) first.  After that, each line shows the start/end
address, size, and the number of observed accesses of each region.


### heats

The `raw` output is very detailed but hard to manually read.  `heats`
sub-subcommand plots the data in 3-dimensional form, which represents the time
in x-axis, address of regions in y-axis, and the access frequency in z-axis.
Users can optionally set the resolution of the map (`--resol`) and start/end
point of each axis (`--time_range` and `--address_range`).  For example:

    # damo report heats --resol 3 3
    0               0               0.0
    0               7609002         0.0
    0               15218004        0.0
    66112620851     0               0.0
    66112620851     7609002         0.0
    66112620851     15218004        0.0
    132225241702    0               0.0
    132225241702    7609002         0.0
    132225241702    15218004        0.0

This command shows a recorded access pattern in a heatmap of 3x3 resolution.
Therefore it shows 9 data points in total.  Each line shows each of the data
points.  The three numbers in each line represent time in nanoseconds, address
in bytes and the observed access frequency.

Users can convert this text output into a heatmap image (represents z-axis
values with colors) or other 3D representations using various tools such as
`gnuplot`.  For more convenience, `heats` sub-subcommand provides the `gnuplot`
based heatmap image creation.  For this, `--heatmap` option can be used.  Also,
note that because it uses `gnuplot` internally, it will fail if `gnuplot` is
not installed on your system.  For example:

    $ ./damo report heats --heatmap heatmap.png

Creates the heatmap image in ``heatmap.png`` file.  It supports ``pdf``,
``png``, ``jpeg``, and ``svg``.

If the target address space is a virtual memory address space and the user
plots the entire address space, the huge unmapped regions will make the picture
looks only black.  Therefore the user should do proper zoom in / zoom out using
the resolution and axis boundary-setting arguments.  To make this effort
minimal, `--guide` option can be used as below:

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

### wss

The `wss` type extracts the distribution and chronological working set size
changes from the record.

By default, the working set is defined as memory regions shown any access
within each snapshot.  Hence, for example, if a record is having N snapshots,
the record is having N working set size values, and `wss` report type shows the
distribution of the N values in size order, or chronological order.

For example:

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

Similar to that of ``heats --heatmap``, it also supports `gnuplot` based simple
visualization of the distribution via ``--plot`` option.

### footprints

Note: This is an experimental feature at the moment.  Some changes could be
made, or the support can be dropped in future.

The `footprints` type extracts the distribution of the
[recorded](#recording-memory-footprints) in chronological or size order.  By
comparing the output against that of [wss](#wss) report type, users can know
how much memory is being allocated for the workload and what amount of the
allocated memory is really being accessed.  The output format is similar to
that of [wss](#wss).

Because there are various memory footprint metrics, the command asks users to
specify what memory footprint metric they want to visualize.  Currently, below
metrics are supported.

- `vsz`: The amount of virtual memory that allocated to the workloads; a.k.a
  "virtual set size".
- `rss`: The amount of physical memory that allocated to the workloads; a.k.a
  "residential set size".
- `sys_used`: The amount of system's memory that allocated for any usage
  (`MemTotal - MemFree`).

For example:

    $ ./damo report footprints vsz
    # <percentile> <footprint>
    # avr:  199.883 MiB
      0     199.883 MiB |***********************************************************|
     25     199.883 MiB |***********************************************************|
     50     199.883 MiB |***********************************************************|
     75     199.883 MiB |***********************************************************|
    100     199.883 MiB |***********************************************************|
    $
    $ ./damo report footprints rss
    # <percentile> <footprint>
    # avr:  196.168 MiB
      0     196.168 MiB |***********************************************************|
     25     196.168 MiB |***********************************************************|
     50     196.168 MiB |***********************************************************|
     75     196.168 MiB |***********************************************************|
    100     196.168 MiB |***********************************************************|

### profile

Note: This feature is an experimental one.  Some changes could be made, or the
support can be dropped in future.

The `profile` type shows profiling report for specific access pattern.

It requires two files, namely an access pattern record file and a profiling
information record file that recorded together with the access pattern record
file.  Those can be generated by `damo record` (Refer to 'Recording Profile
Information' [section](#recording-profile-information) for details).  Users can
further describe access pattern of their interest that they want to know what
happens when the access pattern occurs.  Then, `damo report profile` command
read the access pattern, find times when the specific access pattern happened,
collect profiling information for the time ranges, and generate the report with
the filtered information.

For example, below shows what was consuming CPU while 50% or more rate of
access was made towards 50 MiB size address range starting from
`139,798,348,038,144`, and the total size of the memory regions that got the
access in the address range was 40 or more MiB.

    $ sudo ./damo report profile --access_rate 50% 100% \
            --address 139798348038144 $((139798348038144 + 50 * 1024 * 1024)) \
            --sz_snapshot 40MiB max
    Samples: 69K of event 'cpu-clock:pppH', Event count (approx.): 17449500000
    Overhead  Command          Shared Object         Symbol
      70.32%  swapper          [kernel.vmlinux]      [k] pv_native_safe_halt
      28.83%  masim            masim                 [.] do_seq_wo
       0.03%  masim            [kernel.vmlinux]      [k] _raw_spin_unlock_irqrestore
       0.03%  ps               [kernel.vmlinux]      [k] do_syscall_64
       0.03%  swapper          [kernel.vmlinux]      [k] __do_softirq

### times

Note: This feature is an experimental one.  Some changes could be made, or the
support can be dropped in future.

The `times` type shows time intervals in an access pattern record that showing
specific access pattern.  This can be useful when user runs `damo` together
with other tools such as profilers.

For example, below shows when there was no access to 50 MiB size address range
starting from `139,798,348,038,144`.

    $ sudo ./damo report times --access_rate 0% 0% \
            --address 139798348038144 $((139798348038144 + 50 * 1024 * 1024))
    93904.291408-93904.393156
    93905.919058-93910.903176
    93915.994039-93920.876248
    93926.049032-93930.918094
    93935.988105-93940.956402
    93946.027539-93950.997432
    93956.067597-93961.036500
    93966.101779-93966.910657

### holistic

Note: This is an experimental feature at the moment.  Many changes would be
made, or the support can be dropped in future.

The `holistic` type shows holistic view of the recorded access pattern, memory
footprints, and CPU consuming functions.  As of v2.4.1, it shows access heatmap
and distributions of working set size and memory footprints.  It will further
updated to provide more detailed information in a concise manner, and add the
hot functions information.

For example:

```
$ sudo damo record "./masim ./configs/stairs.cfg"
[...]
$ sudo damo report holistic
# Heatmap
# target 0, address range 94737092173824-94737384947712
00000000000000000000000000000000000000000000000000000000000000000000000000000000
00000000000000000000000000000000000000000000000000000000000000000000000000000000
00000000000000000000000000000000000000000000000000000000000000000000000000000000
00000000000000000000000000000000000000000000000000000000000000000000000000000000
00000000000000000000000000000000000000000000000000000000000000000000000000000000
# x-axis: space (94737092173824-94737384947664: 279.211 MiB)
# y-axis: time (12681562920000-12741660534000: 1 m 0.098 s)
# resolution: 80x5 (3.490 MiB and 12.020 s for each character)
# target 0, address range 140223579160576-140223690682368
33333222222222222222222222222222222222232222222222222222222222222223666666500000
00000000000000000000000000000000000000000000000000002666677567777773333333300000
00000000000000000000000000000022222223777778667777772000000000000000000000000000
00000000000000045555554777777545555551000000000000000000000000000000000000000000
77777885777777512222220000000000000000000000000000000000000000000000000000000000
# x-axis: space (140223579160576-140223690682336: 106.355 MiB)
# y-axis: time (12681562920000-12741660534000: 1 m 0.098 s)
# resolution: 80x5 (1.329 MiB and 12.020 s for each character)
# target 0, address range 140725996015616-140725996150784
00000000000000000000000000000000000000000000000000000000000000000000000000068888
00000000000000000000000000000000000000000000000000000000000000000000000000068888
00000000000000000000000000000000000000000000000000000000000000000000000000067777
00000000000000000000000000000000000000000000000000000000000000000000000000067777
00000000000000000000000000000000000000000000000000000000000000000000000000067777
# x-axis: space (140725996015616-140725996150736: 131.953 KiB)
# y-axis: time (12681562920000-12741660534000: 1 m 0.098 s)
# resolution: 80x5 (1.649 KiB and 12.020 s for each character)

# Memory Footprints Distribution
percentile               0              25              50              75             100
       wss             0 B       9.547 MiB       9.566 MiB       9.828 MiB     106.363 MiB
       rss     100.879 MiB     100.879 MiB     100.879 MiB     100.879 MiB     100.879 MiB
       vsz     104.535 MiB     104.535 MiB     104.535 MiB     104.535 MiB     104.535 MiB
  sys_used       2.159 GiB       2.234 GiB       2.241 GiB       2.245 GiB       2.253 GiB

# Hotspot functions
# Samples: 680K of event 'cpu-clock:pppH'
# Event count (approx.): 170020000000
#
# Overhead  Command          Shared Object                          Symbol                               
# ........  ...............  .....................................  ...........................................
#
    63.01%  swapper          [kernel.vmlinux]                       [k] pv_native_safe_halt
    34.96%  masim            masim                                  [.] do_seq_wo
     0.08%  python3          python3.11                             [.] _PyEval_EvalFrameDefault
     0.07%  ps               [kernel.vmlinux]                       [k] do_syscall_64
     0.05%  ps               [kernel.vmlinux]                       [k] memset_orig
     0.04%  ps               libc.so.6                              [.] open64
     0.04%  perf             perf                                   [.] __symbols__insert
     0.03%  ps               libc.so.6                              [.] read
     0.03%  ps               libc.so.6                              [.] __close
     0.03%  ps               [kernel.vmlinux]                       [k] __memcg_slab_post_alloc_hook
```

`damo replay` (Replay Recorded Data Access Pattern)
---------------------------------------------------

Note: This feature is an experimental one.  Some changes could be made, or the
support can be dropped in future.

`damo replay` receives a `damo record`-generated data access pattern record
file that specified via command line argument (`./damon.data` by default).
Then, the command reproduces the recorded accesses in the file by making
articial memory accesses.  This could be useful for some types of system
analysis or experiments with real-world memory access pattern.

Note that current implementation of `damo replay` runs on Python with single
thread.  Hence it might not performant enough to saturate full memory bandwidth
of the system.  If the record is made by workloads and/or systems that utilize
memory bandwidth more than 'damo replay' and/or replaying systems could, and as
the difference of the performance is big, the replayed accesses would be less
similar to the original one.  To show the real memory access performance of
`damo replay` on specific system, users could use `--test_perf` option.

Miscellaneous Helper Commands
=============================

Abovely explained commands are all core functions of `damo`.  For more
convenient use of `damo` and debugging of DAMON or `damo` itself, `damo`
supports more commands.  This section explains some of those that could be
useful for some cases.

`damo args`
-----------

Some commands including `damo start` and `damo show` have long lists of command
line options.  Those makes flexible usage of `damo`, but makes the help message
too verbose.  For easy handling of such arguments, `damo args` receives such
command line options and outputs compiled parameters.  The output is in a
format like json, which users can read and modify using dedicatd editors.  The
output can also be passed to relevant commands instead of the command line
options.

### `damo args damon`

As mentioned for `damo start` above, DAMON control commands including `start`,
`tune`, and additionally `record` allows passing DAMON parameters or DAMOS
specification all at once via json or yaml formats.  That's for making
specifying and managing complex requests easier, but writing the whole json or
yaml manually could be annoying, while the partial DAMON/DAMOS parameters setup
command line options are easy for simple use case.  To help formatting the json
or yaml input easier, `damo args damon` receives the partial DMAON/DAMOS
parameters setup options and print out resulting json format Kdamond
parameters.  For example,

    # damo args json --damos_action stat

prints json format DAMON parameters specification that will be result in a
DAMON configuration that same to one that can be made with `damo start
--damos_action stat`.  In other words, `damo start $(damo args damon
--damos_action stat)` will be same to `damo start --damos_action stat`.

`damo dianose`
--------------

Note: This is an experimental feature at the moment.  Some changes could be
made, or the support can be dropped in future.

`damo diagnose` prints the status of DAMON and any behaviors that suspicious to
be bugs of DAMON.  Hence, the command can be useful for investigation of DAMON
bugs.  When you report any issue for DAMON that not easy to be reproduced,
providing the 'damo diagnose' output together with the issue report can be
helpful.

`damo version`
--------------

`damo version` shows the version of the installed `damo`.  The version number
is constructed with three numbers.  `damo` is doing chronological release
(about once per week), so the version number means nothing but the relative
time of the release.  Later one would have more features and bug fixes.

`damo fmt_json`
---------------

Note: This command will be deprecated by 2024-11.  Use
`damo args damon --format json` instead.  Please report your usecase to GitHub
[issues](https://github.com/damonitor/damo/issues), sj@kernel.org,
damon@lists.linux.dev and/or linux-mm@kvack.org if you depend on this command.

As mentioned for `damo start` above, DAMON control commands including `start`,
`tune`, and additionally `record` allows passing DAMON parameters or DAMOS
specification all at once via json or yaml formats.  That's for making
specifying and managing complex requests easier, but writing the whole json or
yaml manually could be annoying, while the partial DAMON/DAMOS parameters setup
command line options are easy for simple use case.  To help formatting the json
or yaml input easier, `damo fmt_json` receives the partial DMAON/DAMOS
parameters setup options and print out resulting json format Kdamond
parameters.  For example,

    # damo fmt_json --damos_action stat

prints json format DAMON parameters specification that will be result in a
DAMON configuration that same to one that can be made with `damo start
--damos_action stat`.  In other words, `damo start $(damo fmt_json
--damos_action stat)` will be same to `damo start --damos_action stat`.

For yaml format input, users can simply convert the json input to a valid yaml
format, using common tools.

Note that starting DAMON with the partial DAMON parameter command line option
and then getting the DAMON parameters in the json format using `damo status`
could also be one way for easily starting write of the json format
specification.
