# add to .radssh_config:
# plugins.setpath.dirs=/sbin:/usr/sbin

# Keep path elements as list
add_paths = []

def init(**kwargs):
    # Pull the defined dirs from the config setting
    add_paths.extend(kwargs['defaults'].get('plugins.setpath.dirs').split(':'))

def command_listener(cmd):
    # Munge the path setting if we have additional dirs as a prefix to 
    # the command line, as entered.
    if (cmd and add_paths):
        return 'PATH=${PATH}:%s; %s' % (':'.join(add_paths), cmd)
