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
RadSSH Main Module
==================

Rather than defaulting to running a RadSSH Shell session, this main module
just reports on version information on RadSSH itself, and the strict dependent
modules. This information list should be included in any bug reports.

It also runs a few basic limit checks to determine the maximum concurrent
threads and open file handles for the runtime environment. These two limits
factor into the maximum number of simultaneous connections that RadSSH
can manage.
'''
import os
import sys
import time
import platform
import threading

import ipaddress
import radssh
import paramiko

# Paramiko 2.0 switched dependency from PyCrypto to cryptography.io
if paramiko.__version_info__ >= (2, 0):
    import cryptography as crypto_module
else:
    import Crypto as crypto_module


def open_file(name):
    """
    Return an open file object.
    """
    return open(name)


def start_thread(event):
    """
    Start a thread that waits on a given event, then terminates.
    Used for determining how many threads can be successfully
    started before Python or OS reaches an upper limit.
    """

    def dummy_thread(event):
        """
        Simply wait on event to keep thread active.
        """
        event.wait()

    t = threading.Thread(target=dummy_thread, args=(event,))
    t.start()
    return t


if __name__ == '__main__':
    print('RadSSH Runtime Information Report')
    print(f'Package RadSSH {radssh.version} from ({radssh.__file__})')
    # Dependent modules - Print version and location
    print('  Using Paramiko ', paramiko.__version__, 'from', paramiko.__file__)
    print('  Using', crypto_module.__name__, crypto_module.__version__, 'from', crypto_module.__file__)
    print('  Using ipaddress', ipaddress.__version__ if hasattr(ipaddress, '__version__') else 'built-in', 'from', ipaddress.__file__)
    print()

    # Runtime environment info
    print(f'Python {platform.python_version()} ({platform.python_implementation()})')
    print('Running on', platform.system(), platform.release(), f'[{platform.node()}]')
    if platform.system() == 'Linux':
        # Use distro if available for details, otherwise fallback to platform.platform
        try:
            import distro
            print(f"  {distro.linux_distribution()[0]} ({'/'.join([fld for fld in distro.linux_distribution()[1:] if fld])})")
        except ImportError:
            print(f'  {platform.platform()}')
    print('Encoding for stdout:', sys.stdout.encoding)

    # Test runtime limits of open files and threads
    print('\nChecking runtime limits...')
    lim = []
    t0 = time.time()
    try:
        for x in range(10000):
            lim.append(open_file(os.devnull))
    except Exception as e:
        print(f'  System is able to open a maximum of {len(lim)} concurrent files')
        print(f'    Attempting to open file #{int(len(lim) + 1)} reported ({repr(e)})')
    else:
        print(f'  System is able to open at least {len(lim)} concurrent files')
    finally:
        t1 = time.time()
        print(f'  File check completed in {t1 - t0:f} seconds\n')
        while lim:
            lim.pop().close()
    t0 = time.time()
    kill_threads = threading.Event()
    try:
        for x in range(10000):
            lim.append(start_thread(kill_threads))
    except Exception as e:
        print(f'  System is able to run {len(lim)} concurrent threads')
        print(f'    Attempting to start thread #{int(len(lim) + 1)} reported ({repr(e)})')
    else:
        print(f'  System is able to run {len(lim)} concurrent threads')
    finally:
        t1 = time.time()
        print(f'  Thread check completed in {t1 - t0:f} seconds\n')
        kill_threads.set()
        while lim:
            lim.pop().join()
    print('End of runtime check')
