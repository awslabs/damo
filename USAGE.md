This document describes the detailed usage of `damo`.  This doesn't cover all
details of `damo` but major features.  This document may not complete and up to
date sometimes.  Please don't hesitate at asking questions and improvement of
this document via GitHub [issues](https://github.com/awslabs/damo/issues) or
[mails](https://lore.kernel.org/damon).


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
deprecated.  Please use sysfs.  If you depend on DAMON debugfs interface and
cannot use sysfs interface, report your usecase to sj@kernel.org,
damon@lists.linux.dev and linux-mm@kvack.org.


Perf
----

`damo` uses `perf`[1] for recording DAMON's access monitoring results.  Please
ensure your system is having it if you will need to do record DAMON's
monitoring resluts.  If you will not do the recording, you don't need to
install `perf` on your system, though.

[1] https://perf.wiki.kernel.org/index.php/Main_Page


Basic Concepts of DAMON
-----------------------

`damo` is a user space tool for `DAMON`.  Hence, for advanced and optimized use
of `damo` rather than simple "Getting Started" tutorial, you should first
understand the concepts of DAMON.  There are a number of links to resources
including DAMON introduction talks and publications at the project
[site](https://damonitor.githubio).  The official design
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
available commands and brief descripton of those via `damo --help`.  The major
commands can be categorized as below:

- For controlling DAMON (monitoring and monitoring-based system optimization)
  - `start`, `tune`, and `stop` are included
- For snapshot and visualization of DAMON's monitoring results and running
  status
  - `show`, and `status` are included
- For recording the access monitoring results and visualizing those
  - `record` and `report` are included
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

The command recieves one positional argument called deducible target.  It could
be used for specifying monitoring target, or full DAMON parameters in a json
format.  The command will try to deduce the type of the argument value and use
it.

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

Users can specify full DAMON parameters at once in json format, by passing the
json string of a path to a file containing the json string.  Refer to "Full
DAMON Parameters Update" section below for the detail of the concept, and
"`damo fmt_json`" section below for the format of the json input.

### Partial DAMON Parameters Update

The command line options basically support specification of partial DAMON
parameters such as monitoring intervals and DAMOS action, assuming single
kdamond and single DAMON context.  With a good understanding of DAMON's core
concepts, understanding what each of such options mean with their brief
description on the help message wouldn't be that difficult.

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
It receives a json-format specification of kdamonds that would contains all
DAMON parameters.  Then, `damo` starts DAMON with the specification.

For the format of the json input, please refer to `damo fmt_json` documentation
below, or simply try the command.  The `--kdamonds` option keyword can also
simply omitted because the json input can used as is for the `deducible target`
(refer to "Simple Target Argument" section above).

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
[repo](https://github.com/awslabs/damon-tests/tree/next/perf/schemes).


`damo tune`
-----------

`damo tune` updates the DAMON parameters while DAMON is running.  It provides
the set of command line options that same to that of `damo start`.  Note that
users should provide the full request specification to this command.  If only a
partial parameters are specified via the command line options of this command,
unspecified parameters of running DAMON will be updated to their default
values.

The command exits immediately after updating DAMON parameters as requested.  It
exits with exit value `0` if the update successed.  Otherwise, the exit value
will be non-zero.


`damo stop`
-----------

`damo stop` stops the running DAMON.

The command exits immediately after stopping DAMON.  It exists with exit value
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
of the option receives a string for the template.  The template can have
special format keywords for each position, e.g., `<start address>`, `<end
address>`, `<access rate>`, or `<age>` keywords is available to be used for
`--foramt_region` option's value.  The template can also have arbitrary
strings.  The newline character (`\n`) is also supported.  Each of the keywords
for each position can be shown via
`--ls_{record,snapshot,region}_format_keywords` option.  Actually, `damo show`
also internally uses the customization feature with its default templates.

#### Region Visualization

For region information customization, a special keyword called `<box>` is
provided.  It represents each region's access pattern with its length, color,
and height.  By default it represents each region's age, access rate
(`nr_accesses`), and size with its length, color, and height.  That is,
`damo show --format_region "<box>"` shows visualization of the access pattern,
by showing location of each region in Y-axis, the hotness with color of each
box, and how long the hotness has continued in X-axis.

For convenient use of it with a default format, `damo show` provides
`--region_box` option.  Output of the command with the option would help users
better to understand.

Users can further customize the box using `damo show` options that having
`--region_box_` prefix.  For example, users can set what access information to
be represented by the length, color, and height, and whether the values should
be represented in logscale or linearscale.


`damo status`
-------------

`damo status` shows the running status of DAMON.  It shows every kdamond with
the parameters that applied to it, running status (`on` or `off`), and DAMOS
schemes status including its statistics and detailed applied regions
information.

Note that users can use `--json` to represent the status in a json format.  And
the json format output can again be used for `--kdamonds` or the positional
options of DAMON control commands (`start` and `tune`).

The command exits immediately after showing the current status.  It exists with
exit value `0` if it successfully retrieved and shown the status of DAMON.
Otherwise, the exit value will be non-zero.


For recording the access monitoring results and visualizing those
=================================================================

`damo show` shows only a snapshot.  Since it contains the `age` of each region,
it can be useful for online profiling or debugging.  For offline profiling or
debugging, though, recording changing monitoring results and analyzing the
record could be more helpful.  In this case, the `record` would same to that
for `damo show`, but simply contains multiple `snapshot`s.

Recording Data Access Pattern
-----------------------------

The ``record`` subcommand records the data access pattern of target workloads
in a file (``./damon.data`` by default).  The path to the file can be set with
`--out` option.  The output file will be owned by ``root`` and have ``600``
permission by default, so only root can read it.  Users can change the
permission via ``--output_permission`` option.

Other than the two options, `damo record` receives command line options that
same to those for `damo start` and `damo tune`.  If DAMON is already running,
you can simply record the monitoring results of the running DAMON by providing
no DAMON parameter options.  For example, below will start DAMON for physical
address space monitoring, record the monitoring results, and save the records
in `damon.data` file.

    # damo start
    # damo record

Or, you can ask `damo start` to also start DAMON, together with the monitoring
target command, like below:

    # damo record "sleep 5"

or, for already running process, like below:

    # damo record $(pidof my_workload)


Visualizing Recorded Data Access Pattern
----------------------------------------

The ``report`` subcommand reads a data access pattern record file (if not
explicitly specified using ``-i`` option, reads ``./damon.data`` file by
default) and generates human-readable reports.  You can specify what type of
report you want using a sub-subcommand to ``report`` subcommand.  ``raw``,
``heats``, and ``wss`` report types are supported for now.

### raw

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


### heats

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


### wss

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


Miscelleneous Helper Commands
=============================

Abovely explained commands are all core functions of `damo`.  For more
convenient use of `damo` and debugging of DAMON or `damo` itself, `damo`
support more commands.  This section explains some of those that could be
useful for some cases.

`damo version`
--------------

`damo version` shows the version of the installed `damo`.  The version number
is constructed with three numbers.  `damo` is doing chronological release
(about once per week), so the version number means nothing but the relative
time of the release.

`damo fmt_json`
---------------

As mentioned for `damo start` above, DAMON control commands including `start`,
`tune`, and additionally `record` allows passing DAMON parameters or DAMOS
specification all at once via a json format.  That's for making specifying and
managing complex request easier, but writing the whole json manually could be
annoying, while the partial DAMON/DAMOS parameters setup command line options
are easy for simple use case.  To help formatting the json input easier, `damo
fmt_json` receives the partial DMAON/DAMOS parameters setup options and print
out resulting json format Kdamond parameters.  For example,

    # damo fmt_json --damos_action stat

prints json format DAMON parameters specification that will be result in a
DAMON configuration that same to one that can be made with `damo start
--damos_action stat`.  In other words, `damo start $(damo fmt_json
--damos_action stat)` will be same to `damo start --damos_action stat`.
