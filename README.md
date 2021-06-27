DAMO: DAMon Operator
====================

This directory contains a user space tool for DAMON[1], namely ``damo``.  Using
the tool, you can monitor the data access patterns of your system and make data
access-aware memory management optimizations.

[1] https://damonitor.github.io

![damo monitor demo for water_nsquared](for_doc/damo_monitor_water_nsquared.gif)


Demo Video
==========

Please click below thumbnail to show the short demo video.

[![DAMON: a demo for the Kernel Summit 2020](
http://img.youtube.com/vi/l63eqbVBZRY/0.jpg)](
http://www.youtube.com/watch?v=l63eqbVBZRY
"DAMON: a demo for the Kernel Summit 2020")


Getting Started
===============

Follow below instructions and commands to monitor and visualize the access
pattern of your workload.

    $ git clone https://github.com/sjp38/linux -b damon/master
    /* build the kernel with CONFIG_DAMON_*=y, install, reboot */
    $ mount -t debugfs none /sys/kernel/debug/
    $ ./damo record $(pidof <your workload>)
    $ ./damo report heats --plot stdout --stdout_heatmap_color emotion

The last command will show the access pattern of your workload, like below:

![masim zigzag heatmap in ascii](for_doc/masim_zigzag_heatmap_ascii.png)
![masim stairs heatmap in ascii](for_doc/masim_stairs_heatmap_ascii.png)

Below sections further provide quick introductions for `damo`'s major features.
For more detailed usage, please refer to [USAGE.md](USAGE.md) file.


Recording Data Access Patterns
==============================

Below commands record memory access pattern of a program and save the
monitoring results in a file.

    $ git clone https://github.com/sjp38/masim
    $ cd masim; make; ./masim ./configs/zigzag.cfg &
    $ sudo ./damo record -o damon.data $(pidof masim)

The first two lines of the commands get an artificial memory access generator
program and runs it in the background.  It will repeatedly access two 100 MiB
sized memory regions one by one.  You can substitute this with your real
workload.  The last line asks ``damo`` to record the access pattern in
``damon.data`` file.


Visualizing Recorded Patterns
=============================

Below three commands visualize the recorded access patterns into three
image files.

    $ damo report heats --heatmap access_pattern_heatmap.png
    $ damo report wss --range 0 101 1 --plot wss_dist.png
    $ damo report wss --range 0 101 1 --sortby time --plot wss_chron_change.png

- ``access_pattern_heatmap.png`` will show the data access pattern in a
  heatmap, which shows when (x-axis) what memory region (y-axis) is how
  frequently accessed (color).
- ``wss_dist.png`` will show the distribution of the working set size.
- ``wss_chron_change.png`` will show how the working set size has
  chronologically changed.

You can show the images in a web page [1].  Those made with other realistic
workloads are also available [2,3,4].

[1] https://damonitor.github.io/doc/html/latest/admin-guide/mm/damon/start.html#visualizing-recorded-patterns  
[2] https://damonitor.github.io/test/result/visual/latest/rec.heatmap.1.png.html  
[3] https://damonitor.github.io/test/result/visual/latest/rec.wss_sz.png.html  
[4] https://damonitor.github.io/test/result/visual/latest/rec.wss_time.png.html


Data Access Pattern Aware Memory Management
===========================================

Below three commands make every memory region of size >=4K that doesn't
accessed for >=60 seconds in your workload to be swapped out.  By doing this,
you can make your workload more memory efficient with near-zero performance
overhead.

    $ echo "#min-size max-size min-acc max-acc min-age max-age action" > scheme
    $ echo "4K        max      0       0       60s     max     pageout" >> scheme
    $ damo schemes -c my_thp_scheme <pid of your workload>


System Disgn
============

Below shows how `damo` works with DAMON/DAMOS in kernel.

                       ┌──────┐
           ┌───────────┤ DAMO │
           │Read       └──┬───┘
           ▼              │read/write
      ┌──────────┐        ▼
      │Monitoring│   ┌─────────┐       User space
    ──┤  reuslt  ├───┤ debugfs ├─────────────────
      │   file   │   └─┬─────┬─┘     Kernel space
      └──────────┘     │     │Operation scheme
           ▲           │     ▼
           │    Monitor│  ┌──────────────┐
           │    request│  │     DAMOS    │
           │           │  └────────────┬─┘
           │           │   ▲ Monitor   │
           │           │   │ request/  │
           │           ▼   ▼ response  │Control
           │Write┌────────────┐        │swap,
           └─────┤   DAMON    │        │LRU,
                 └──────┬─────┘        │THP
                        │Check access  │
                        ▼              ▼
                 ┌───────────────────────┐
                 │         Memory        │
                 └───────────────────────┘
