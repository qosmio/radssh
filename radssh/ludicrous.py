# Ludicrous Speed Plugin
'''
Patch up RadSSH/Paramiko settings to achieve top throughput, at the
expense of security.
'''

import time
import pprint

import paramiko
import radssh
import radssh.known_hosts


def null_hostkey_verify(*args):
	# print 'Null Hostkey Verify', args
	return True


def init(*args, **kwargs):
	print '*** Ludicrous Speed ***'
	# print args
	# pprint.pprint(kwargs)
	radssh.known_hosts.verify_transport_key = null_hostkey_verify

	# Patch in priority list of Paramiko Transport client preferences
	# See http://homepages.warwick.ac.uk/staff/E.J.Brambley/sshspeedtest.php
	# for the speed choices to identify likely candidates for top throughput

	#>>> paramiko.Transport._preferred_macs
	#('hmac-sha2-256', 'hmac-sha2-512', 'hmac-md5', 'hmac-sha1-96', 'hmac-md5-96', 'hmac-sha1')
	paramiko.Transport._preferred_macs = (
		'hmac-md5',
		'hmac-md5-96',
		'hmac-sha1-96',
		'hmac-sha1',
		'hmac-sha2-256',
		'hmac-sha2-512',
	)

	# >>> paramiko.Transport._preferred_kex
	# ('diffie-hellman-group1-sha1', 'diffie-hellman-group14-sha1', 'diffie-hellman-group-exchange-sha1', 'diffie-hellman-group-exchange-sha256')
	# Key Exchange - minimal speed impact (?)

	# >>> paramiko.Transport._preferred_ciphers
	# ('aes128-ctr', 'aes192-ctr', 'aes256-ctr', 'aes128-cbc', 'blowfish-cbc', 'aes192-cbc', 'aes256-cbc', '3des-cbc', 'arcfour128', 'arcfour256')
	paramiko.Transport._preferred_ciphers = (
		# 'arcfour128',
		# 'arcfour256',
		'aes128-cbc',
		'aes192-cbc',
		'aes256-cbc',
		'aes128-ctr',
		'aes192-ctr',
		'aes256-ctr',
		'blowfish-cbc',
		'3des-cbc',
	)
	
