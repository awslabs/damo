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

def max_color_level():
    return len(colorsets['gray'][0]) - 1

def colored(txt, colorset_name, level, reset_color_mode=True):
    if not colorset_name in colorsets:
        raise Exception('wrong colorset (%s)' % colorset)

    colorset = colorsets[colorset_name]
    bg = colorset[0][level]
    fg = colorset[1][level]
    color_prefix = u'\u001b[48;5;%dm\u001b[38;5;%dm' % (bg, fg)
    if not reset_color_mode:
        return color_prefix + txt
    color_suffix = u'\u001b[0m'
    return color_prefix + txt + color_suffix
