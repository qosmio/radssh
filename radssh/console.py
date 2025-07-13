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

'''
RadSSH Console
==============
Handle output text streamed to a Queue to present on terminal.

Messages are expected to be tagged as to their origin, expected
to be a pair (label, stderr), where label is typically a hostname
and stderr is a boolean indicating if the message content came from
stderr (highlight) or not.
'''
import sys
import threading
import getpass
import ipaddress
from collections import deque, defaultdict
import queue


console_mutex = threading.Lock()


def user_input(prompt):
    with console_mutex:
        answer = input(prompt)
    return answer


def user_password(prompt):
    with console_mutex:
        answer = getpass.getpass(prompt)
    return answer


def monochrome(tag, text, max_label_width=0):
    '''Basic Formatter for plain (monochrome) output'''
    label, _ = tag
    if max_label_width > 0:
        label = label.rjust(max_label_width)
    for line in text.split('\n'):
        yield f'{label}| {line}\n'


def colorizer(tag, text, max_label_width=0):
    '''Basic ANSI colorized output - host hash value map to 7-color palette, stderr bold'''
    label, hilight = tag
    if max_label_width > 0:
        label = label.rjust(max_label_width)
    color = 1 + hash(label.strip()) % 7
    for line in text.split('\n'):
        if hilight:
            yield f'\x1b[30;4{int(color)}m{label}|\x1b[0;1;3{int(color)}m {line}\x1b[0m\n'
        else:
            yield f'\x1b[3{int(color)}m{label}| {line}\x1b[0m\n'


class RadSSHConsole:
    '''
    Combine a Queue object with a daemon thread that pulls message
    output from the queue and pretties it up for on screen display.
    When run in a terminal window, uses ANSI escape sequences to
    colorize output, and use the window/tab title for status messages.
    '''
    def __init__(self, q=None, formatter=colorizer, retain_recent=0, hostlist=None):
        if q:
            self.q = q
        else:
            self.q = queue.Queue(300)
        self.formatter = formatter
        self.quietmode = False
        # Calculate maximum label width for right-alignment
        self.max_label_width = 0
        self.hostlist = hostlist
        if hostlist:
            label_widths = []
            for label, _ in hostlist:
                if isinstance(label, ipaddress.IPv4Address) or isinstance(label, ipaddress.IPv6Address):
                    label = label.compressed
                label_widths.append(len(label))
            self.max_label_width = max(label for label in label_widths)
        self.background_thread = threading.Thread(target=self.console_thread, args=())
        self.background_thread.setDaemon(True)
        self.background_thread.setName('Console Output')
        self.background_thread.start()

        def limit_deque():
            return deque([], retain_recent)

        self.retain_recent = retain_recent
        self.recent_history = defaultdict(limit_deque)

    def quiet(self, enable=True):
        '''Set (or clear) console quietmode. Returns prior setting.'''
        # Wait for queue to drain before taking effect
        self.q.join()
        retval = self.quietmode
        self.quietmode = enable
        return retval

    def status(self, message):
        '''Set console (titlebar) status message'''
        if not self.quietmode:
            # Jam into window title bar
            print(f"\x1b]2;{message}\x07", end='')
            sys.stdout.flush()

    def join(self, clear_history=False):
        self.q.join()
        if clear_history:
            self.recent_history.clear()

    def message(self, message, label='CONSOLE'):
        '''Main thread can submit CONSOLE messages directly through instance'''
        self.q.put(((label, True), str(message)))

    def progress(self, s):
        '''For progress-bar like output; no newlines'''
        if not self.quietmode:
            with console_mutex:
                print(s, end='')
                sys.stdout.flush()

    def replay_recent(self, label):
        '''Output the recent lines sent tagged from "label" - Used for Ctrl-C handler'''
        if not self.retain_recent:
            return
        self.join()
        for line in self.recent_history.get(str(label), []):
            print(f"STALLED: {line}", end='')

    def console_thread(self):
        '''Background-able thread to pull from outputQ and format and print to screen'''
        tag = None
        text = None
        while True:
            try:
                tag, text = self.q.get()
                if not self.quietmode:
                    with console_mutex:
                        # Tag is tuple of (label, stderr_flag)
                        try:
                            # Try calling formatter with max_label_width parameter
                            for line in self.formatter(tag, text, self.max_label_width):
                                print(line, end='')
                                if self.retain_recent:
                                    self.recent_history[str(tag[0])].append(line)
                        except TypeError:
                            # Fallback for formatters that don't support max_label_width
                            for line in self.formatter(tag, text):
                                print(line, end='')
                                if self.retain_recent:
                                    self.recent_history[str(tag[0])].append(line)
                        sys.stdout.flush()
            except Exception as e:
                print(f'Console Thread Exception: {str(e)}\n')
                print(f'({tag}): {text}\n')
            finally:
                self.q.task_done()


if __name__ == '__main__':
    c = RadSSHConsole(queue.Queue(300))
    c.message('Begin Console Output')
    c.status('Title Bar Set')
    for x in range(20):
        c.q.put((('Loop', False), str(x)))
    print('Loop complete\n', end='')
    c.join()
    print('Console output complete')
    sys.stdout.flush()
