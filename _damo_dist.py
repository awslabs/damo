# SPDX-License-Identifier: GPL-2.0

import os
import subprocess

'return error'
def plot_dist(data_file, output_file, xlabel, ylabel):
    terminal = output_file.split('.')[-1]
    if not terminal in ['pdf', 'jpeg', 'png', 'svg']:
        os.remove(data_file)
        return 'Unsupported plot output type.'

    gnuplot_cmd = """
    set term %s;
    set output '%s';
    set key off;
    set xlabel '%s';
    set ylabel '%s';
    plot '%s' with linespoints;""" % (terminal, output_file, xlabel, ylabel,
            data_file)
    subprocess.call(['gnuplot', '-e', gnuplot_cmd])
    os.remove(data_file)
    return None
