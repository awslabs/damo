# SPDX-License-Identifier: GPL-2.0

# {name: [[background colors], [foreground colors]]}
colorsets = {
    'gray':[
        [232] * 10,
        [237, 239, 241, 243, 245, 247, 249, 251, 253, 255]],
    'flame':[
        [232, 1, 1, 2, 3, 3, 20, 21,26, 27, 27],
        [239, 235, 237, 239, 243, 245, 247, 249, 251, 255]],
    'emotion':[
        [232, 234, 20, 21, 26, 2, 3, 1, 1, 1],
        [239, 235, 237, 239, 243, 245, 247, 249, 251, 255]],
    }

def colored(txt, colorset, level):
    bg = colorset[0][level]
    fg = colorset[1][level]
    color_prefix = u'\u001b[48;5;%dm\u001b[38;5;%dm' % (bg, fg)
    color_suffix = u'\u001b[0m'
    return color_prefix + txt + color_suffix
