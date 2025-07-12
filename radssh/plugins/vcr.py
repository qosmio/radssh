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

'''Plugin to provide VCR-like capabilities for command lines'''

import os
import atexit
import pprint


vcr = None
shell = None


def init(**kwargs):
    # VCR needs access ot the parent shell for playback
    global shell
    try:
        shell = kwargs['shell']
    except KeyError:
        raise RuntimeError('VCR: Unable to initialize', 'RadSSH shell not accessible')


class Recorder(object):
    def __init__(self, filename, vars={}):
        self.active = True
        self.data = []
        self.filename = filename
        self.vars = vars

    def pause(self):
        self.active = not self.active

    def feed(self, x):
        if self.active:
            self.data.append(x)

    def save(self):
        with open(self.filename, 'a') as f:
            f.write('\n'.join(self.data))
        if self.vars:
            with open(f"{self.filename}.vars", 'w') as f:
                f.write(pprint.pformat(self.vars))


def command_listener(cmd):
    global vcr
    if vcr:
        args = cmd.split()
        if args and not args[0] in star_commands:
            vcr.feed(cmd)


def eject():
    '''Register this as an atexit function to save off vcr session when shell terminates'''
    global vcr
    if vcr:
        print('Auto-saving VCR contents')
        vcr.save()


atexit.register(eject)


def record(cluster, logdir, cmd, *args):
    '''Begin recording of session commands for later playback'''
    global vcr
    if not args:
        if vcr:
            print('Stop Recording')
            vcr.save()
            print(f'Finished recording saved to {vcr.filename} ({len(vcr.data)} lines)')
            vcr = None
        else:
            print('Use "*record <filename>" to begin recording')
        return
    if os.path.sep in args[0]:
        filename = args[0]
    else:
        filename = os.path.join(logdir, args[0])
    if vcr:
        # Save off old recording session
        vcr.save()
        print(f'Saved existing recording to {vcr.filename} ({len(vcr.data)} lines)')
    vcr = Recorder(filename, cluster.user_vars)
    print(f'Started new recording to {filename}')


def pause(cluster, logdir, cmd, *args):
    '''Temporary suspend/resume toggle for VCR-like recording'''
    global vcr
    if not vcr:
        print('VCR not running. Did you put in a tape?')
        return
    vcr.pause()
    if vcr.active:
        print('VCR unpaused')
    else:
        print(f'VCR paused ({len(vcr.data)} lines in buffer)')


def playback(cluster, logdir, cmd, *args):
    '''Playback scripted commands from *record save file, or other script file'''
    if len(args) != 1:
        print('Try "*playback <filename>"')
        return
    filename = args[0]
    if os.path.exists(f"{filename}.vars"):
        print('Loading saved variables...')
        try:
            with open(f"{filename}.vars", 'r') as var_file:
                cluster.user_vars.update(eval(var_file.read()))
        except Exception as e:
            print(f"Failed to load variables from [{filename}].vars")
            print(f'{e!r}')
    with open(filename) as f:
        shell(cluster, logdir, f, cluster.defaults)
    print(f'*** Playback of {filename} complete ***')


star_commands = {'*record': record, '*pause': pause, '*playback': playback}
