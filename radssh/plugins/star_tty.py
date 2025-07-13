#
# Copyright (c) 2014, 2016, 2018, 2020 LexisNexis Risk Data Management Inc.
#
# This file is part of the RadSSH software package.
#
# RadSSH is free software, released under the Revised BSD License.
# You are permitted to use, modify, and redsitribute this software
# according to the Revised BSD License, a copy of which should be
# included with the distribution as file LICENSE.txt
#

'''Sequentially invoke single TTY ssh sessions'''

import sys
import select
import termios
import tty
import os
import fcntl
import time


settings = {
    'prompt_delay': "5.0",
    'rc_file': None
}


def init(**kwargs):
    # If user has set an rc_file, read in the contents
    settings['rc_commands'] = []
    if settings.get('rc_file'):
        try:
            with open(os.path.expanduser(settings.get('rc_file'))) as f:
                for line in f:
                    line = line.strip()
                    if not line.startswith('#'):
                        settings['rc_commands'].append(line)
        except Exception:
            pass


def posix_shell(chan, encoding='UTF-8'):
    partial_buf = b''
    try:
        while True:
            r, w, _ = select.select([chan, sys.stdin], [], [])
            if (chan in r):
                try:
                    x = chan.recv(1024)
                    r1, w1, e1 = select.select([], [sys.stdout], [])
                    if (sys.stdout in w1):
                        if len(x) == 0:
                            sys.stdout.write('\r\n*** EOF ***\r\n')
                            break
                        print((partial_buf + x).decode(encoding), end='')
                        sys.stdout.flush()
                        partial_buf = b''
                except TimeoutError:
                    pass
                except UnicodeError:
                    # Keep the bytes read to append to on next pass
                    partial_buf += x
            if sys.stdin in r:
                x = sys.stdin.read()
                chan.send(x.encode(encoding))
    except Exception as e:
        print(f'Exception in TTY session\n{e!r}\n')


def terminal_size():
    import termios
    import struct
    h, w, hp, wp = struct.unpack('HHHH',
                                 fcntl.ioctl(0, termios.TIOCGWINSZ,
                                             struct.pack('HHHH', 0, 0, 0, 0)))
    return w, h


def radssh_tty(cluster, logdir, cmd, *args):
    '''Invoke a TTY single session'''
    cols, lines = terminal_size()
    if not args:
        args = []
        for k in cluster:
            if k not in cluster.disabled:
                args.append(str(k))

    # Within this tinkering with stdin, output seems
    # to require \r\n for end of line
    oldtty = termios.tcgetattr(sys.stdin)
    tty.setraw(sys.stdin.fileno())
    tty.setcbreak(sys.stdin.fileno())
    old_fcntl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
    fcntl.fcntl(sys.stdin, fcntl.F_SETFL, old_fcntl | os.O_NONBLOCK)
    try:
        prompt_delay = float(settings['prompt_delay'])
    except (ValueError, KeyError):
        prompt_delay = 5.0

    for x in args:
        if not cluster.locate(x):
            print(f'Skipping TTY request for {str(x)} (not found)\r')
            continue
        if prompt_delay:
            try:
                print(f'Starting TTY session for [{x}] in {prompt_delay:g} seconds...\r')
                print(
                    '(Press \'S\' to skip, \'X\' to abort, any other key to connect immediately)',
                    end='')
                sys.stdout.flush()
                r, w, _ = select.select([sys.stdin], [], [], prompt_delay)
                print('\r\n')
                if r:
                    keystroke = sys.stdin.read()
                    if keystroke in ('s', 'S'):
                        continue
                    if keystroke in ('x', 'X'):
                        break
            except Exception as e:
                print(e)
        try:
            session = None
            t = cluster.connections[cluster.locate(x)]
            if not t.is_authenticated():
                print(f'Skipping TTY request for {str(x)} (not authenticated)\r')
                continue
            session = t.open_session()
            session.get_pty(width=cols, height=lines)
            if prompt_delay:
                print(f'Starting TTY session for {str(x)}\r')
            session.invoke_shell()
            if settings['rc_commands']:
                print(f"# sending commands from {settings['rc_file']}\r")
                for line in settings['rc_commands']:
                    session.send(f"{line}\n".encode(cluster.defaults['character_encoding']))
                # Attempt to quietly consume output from the sent commands
                time.sleep(0.2)
                session.recv(65536)
                # And send an additional newline, to force new prompt line
                session.send('\n')
            posix_shell(session, cluster.defaults['character_encoding'])
            if prompt_delay:
                print(f'TTY session for {str(x)} completed\r')
            session.close()
        except Exception as e:
            print(f'Exception occurred while trying TTY for {str(x)}\r')
            print(repr(e))
            if session:
                session.close()
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)
    fcntl.fcntl(sys.stdin, fcntl.F_SETFL, old_fcntl)


star_commands = {'*tty': radssh_tty}
