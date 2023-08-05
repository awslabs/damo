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

def color_mode_start_txt(colorset_name, level):
    if not colorset_name in colorsets:
        raise Exception('wrong colorset (%s)' % colorset)

    colorset = colorsets[colorset_name]
    bg = colorset[0][level]
    fg = colorset[1][level]
    return u'\u001b[48;5;%dm\u001b[38;5;%dm' % (bg, fg)

def color_mode_end_txt():
    return u'\u001b[0m'

def colored(txt, colorset_name, level):
    return ''.join([color_mode_start_txt(colorset_name, level), txt,
        color_mode_end_txt()])

def color_samples(colorset_name):
    samples = []
    for level in range(max_color_level() + 1):
        samples.append('%s%s' % (color_mode_start_txt(colorset_name, level),
            '%d' % level))
    samples.append(color_mode_end_txt())
    return ''.join(samples)

def main():
    for colorset_name in colorsets:
        print('colorset_name')
        print(color_samples(colorset_name))

if __name__ == '__main__':
    main()
