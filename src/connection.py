#!/usr/bin/env python

"""
Strange, but kind of works
"""

import paramiko 

def read_until(chan, s): 
	"""
	Reads until s is found, returns data read
	""" 

	buffer=[] 

	while "".join(buffer[-len(s):]) != s : 
		buffer.append(chan.recv(1)) 
	return "".join(buffer) 

HOST='pl-byd-esxi13-ilo'
ssh=paramiko.Transport((HOST,22))
paramiko.util.log_to_file('/tmp/paramiko.log')
print "..."
ssh.connect(username='Administrator',password='ChangeMe')
print "Connected"
sess = ssh.open_session()
print "Session opened"
sess.get_pty()
print "Got the PTY"
sess.invoke_shell()
print "Invoked the shell"
print read_until(sess, '>')
print "Writing... "
#sess.sendall("set cli-parameters pager off\r")
print "OK"
read_until(sess, '>') # but ignore
sess.sendall("show /system1/sensor3")
print read_until(sess, '>')
sess.sendall("exit\r")
ssh.close()