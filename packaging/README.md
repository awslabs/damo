DAMO: Data Access Monitoring Operator
=====================================

This directory contains a user space tool for
[DAMON](https://damonitor.github.io), namely ``damo``.  Using the tool, you can
monitor the data access patterns of your system or workloads and make data
access-aware memory management optimizations.


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

    $ # ensure your kernel is built with CONFIG_DAMON_*=y
    $ sudo mount -t debugfs none /sys/kernel/debug/
    $ sudo pip3 install damo
    $ sudo damo record $(pidof <your workload>)
    $ damo report heats --plot stdout --stdout_heatmap_color emotion

The last command will show the access pattern of your workload, like below:

![masim zigzag heatmap in ascii](https://raw.githubusercontent.com/awslabs/damo/v0.0.2/images/masim_zigzag_heatmap_ascii.png)
![masim stairs heatmap in ascii](https://raw.githubusercontent.com/awslabs/damo/v0.0.2/images/masim_stairs_heatmap_ascii.png)


FAQs
====

Will `pip3 install damo` install latest version of `damo`?
----------------------------------------------------------

It will install the latest _stable_ version of `damo`.  If you want, you can
also install less stable but more fresh `damo` from source code.  For that,
simply download the `next` branch of the source tree and use `damo` executable
file in the tree.

    $ git clone https://github.com/awslabs/damo -b next
    $ sudo ./damo/damo record $(pidof <your workload>)


How can I participate in the development of `damo`?
---------------------------------------------------

Please refer to
[CONTRIBUTING](https://github.com/awslabs/damo/blob/master/CONTIRUTING) file.


What does the version number means?
-----------------------------------

Nothing at all, but larger version number means it is released more recently.


Where can I get more detailed usage?
------------------------------------

For more detailed usage, please refer to
[USAGE.md](https://github.com/awslabs/damo/blob/v0.0.2/USAGE.md).
