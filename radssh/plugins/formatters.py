#
# Copyright (c) 2018, 2020 LexisNexis Risk Data Management Inc.
#
# This file is part of the RadSSH software package.
#
# RadSSH is free software, released under the Revised BSD License.
# You are permitted to use, modify, and redsitribute this software
# according to the Revised BSD License, a copy of which should be
# included with the distribution as file LICENSE.txt
#

'''
Customizable RadSSH Console formatter module:
Allow plugins to provide formatter function(s) to supplement the
basic monochrome and colorizer formatters included as defaults.

This module can be copied and customized, and loaded as a RadSSH
plugin with an arbitrary name, and multiple formatter functions.

To enable custom formatter, set "shell.console=formatters.ansi256"
'''

import fcntl
import termios
import struct
import re

# See: http://misc.flogisoft.com/bash/tip_colors_and_formatting
# Grab a broad range of colors that avoid the muddled dark on dark contrast
palette = list(range(20, 230))


def ansi256(tag, text, max_label_width=0):
    '''ANSI 256 colorized output with semi-restricted palette'''
    label, hilight = tag
    if max_label_width > 0:
        label = label.rjust(max_label_width)
    color = palette[hash(label.strip()) % len(palette)]
    for line in text.split('\n'):
        if hilight:
            yield f'\x1b[1;38;5;{int(color)}m[{label}] {line}\x1b[0m\n'
        else:
            yield f'\x1b[38;5;{int(color)}m[{label}] {line}\x1b[0m\n'


def ansi256_rj(tag, text, max_label_width=0):
    '''ANSI 256 colorized output, with host label right-justified'''
    label, hilight = tag
    height, width = struct.unpack('hh', fcntl.ioctl(0, termios.TIOCGWINSZ, '1234'))

    color = palette[hash(label) % len(palette)]
    for line in text.split('\n'):
        wide_line = line.ljust(width - len(label) - 2, ' ')
        if hilight:
            yield f'\x1b[1;38;5;{int(color)}m{wide_line}[{label}]\x1b[0m\n'
        else:
            yield f'\x1b[38;5;{int(color)}m{wide_line}[{label}]\x1b[0m\n'


def ip_hash(hstr0):
    '''Improved hashing when dealing with consecutive IP addresses'''
    hstr1 = re.sub('[^0-9]', '.', hstr0)
    hstr2 = hstr1.replace(".", "0")
    hstr = hstr2[-3:]
    hval = int(hstr)
    return hval


def ip_colorizer(tag, text, max_label_width=0):
    '''Alternative ANSI colorized output - ensure that IP address ranges cycle colors more uniformly'''
    # Copied from standard colorizer, but with a custom hash function
    label, hilight = tag
    if max_label_width > 0:
        label = label.rjust(max_label_width)
    color = 1 + ip_hash(str(label.strip())) % 7
    for line in text.split('\n'):
        if hilight:
            yield f'\x1b[30;4{int(color)}m[{label}]\x1b[0;1;3{int(color)}m {line}\x1b[0m\n'
        else:
            yield f'\x1b[3{int(color)}m[{label}] {line}\x1b[0m\n'
