DAMO: DAMon Operator
====================

This directory contains a user space tool for
[DAMON](https://damonitor.github.io), namely ``damo``.  Using the tool, you can
monitor the data access patterns of your system and make data access-aware
memory management optimizations.


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

    $ # build the kernel with CONFIG_DAMON_*=y, install, reboot
    $ sudo mount -t debugfs none /sys/kernel/debug/
    $ sudo pip3 install damo
    $ damo record $(pidof <your workload>)
    $ damo report heats --plot stdout --stdout_heatmap_color emotion

The last command will show the access pattern of your workload, like below:

![masim zigzag heatmap in ascii](https://raw.githubusercontent.com/awslabs/damo/master/for_doc/masim_zigzag_heatmap_ascii.png)
![masim stairs heatmap in ascii](https://raw.githubusercontent.com/awslabs/damo/master/for_doc/masim_stairs_heatmap_ascii.png)

For more detailed usage, please refer to
[USAGE.md](https://github.com/awslabs/damo/blob/master/USAGE.md).
