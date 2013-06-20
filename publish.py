#!/usr/bin/env python
#
# Software License
# 
# Copyright 2001-2013 Chris Gonnerman
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without 
# modification, are permitted provided that the following conditions
# are met:
# 
# Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer. 
# 
# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution. 
# 
# Neither the name of the author nor the names of any contributors
# may be used to endorse or promote products derived from this software
# without specific prior written permission. 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# AUTHOR OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""publish.py -- Publish a local website copy to the webserver

publish.py reads the .site file in the current directory for information
about what to publish, where to put it, and what username and password
are to be used.  Publishing is accomplished with ftplib.

The .site file is formatted as Python code, and should contain the following
variable assignments:

    user = "username"               # username to login with
    pwd = "password"                # password to login with
    host = "hostname"               # host to publish to
    directory = "directory"         # publishing directory on server
    source = "source-directory"     # local directory containing pages
    passive = 0                     # or 1 to specify passive mode
    mode = "ftp"                    # or "copy" to copy the files directly
    lowername = 1                   # change names to lowercase

.index should contain a valid repr() of a dictionary, where the
keys are filenames and the values are lists containing the timestamps,
as returned as element 8 of the stat tuple.  The values have to be
stored in lists because we will be storing a temporary flag there.

.index won't be found the first time through.
"""

# my version numbers are usually strings
__version__ = "2.0"

import os, sys

try:
    import timeoutsocket
    timeoutsocket.setDefaultSocketTimeout(60)
except ImportError:
    pass

##########################################################################
#  NullFTP is used by the touch function
##########################################################################

class NullFTP:
    def nullfunc(self, *args):
        pass
    def __getattr__(self, attr):
        return self.nullfunc

##########################################################################
#  ZipFTP is used in zipping mode
##########################################################################

import zipfile, time

class ZipFTP:
    def __init__(self, fn):
        self.filename = fn
        self.zipfile = zipfile.ZipFile(fn, "w", zipfile.ZIP_DEFLATED)
        self.dirpath = []
    def mkd(self, d):
        pass
    def cwd(self, d):
        if d == ".":
            return
        if d == "..":
            self.dirpath = self.dirpath[:-1]
        else:
            self.dirpath.append(d)
    def storbinary(self, cmd, file, blocksize = None):
        zinfo = zipfile.ZipInfo()
        zinfo.filename = '/'.join(self.dirpath + [ cmd[5:] ])
        zinfo.compress_type = zipfile.ZIP_DEFLATED
        zinfo.flag_bits = 0x08
        try:
            st = os.fstat(file.fileno())
            zinfo.date_time = time.localtime(st[8])[:6]
            zinfo.external_attr = 0x80000000 | (st[0] << 16)
        except:
            zinfo.date_time = (2002, 1, 1, 0, 0, 0)
        self.zipfile.writestr(zinfo, file.read())
    def voidcmd(self, cmd):
        pass
    def login(self, user, pwd):
        pass
    def set_pasv(self, mode):
        pass
    def delete(self, fname):
        pass
    def quit(self):
        self.zipfile.close()

##########################################################################
#  CopyFTP is used in copy mode
##########################################################################

import shutil

class CopyFTP:
    def __init__(self):
        pass
    def mkd(self, d):
        os.mkdir(d)
    def cwd(self, d):
        os.chdir(d)
    def storbinary(self, cmd, file, blocksize = None):
        fname = cmd[5:]
        fp = open(fname, "w")
        shutil.copyfileobj(file, fp)
        fp.close()
    def voidcmd(self, cmd):
        pass
    def login(self, user, pwd):
        pass
    def set_pasv(self, mode):
        pass
    def delete(self, fname):
        os.remove(fname)
    def quit(self):
        pass

##########################################################################
#  SecureFTP provides SFTP (SSH FTP) services using paramiko
##########################################################################

try:
    import paramiko

    class SecureFTP:
        def __init__(self, hostname, port = 22):
            self.hostname = hostname
            self.transport = paramiko.Transport((hostname, port))
        def mkd(self, d):
            self.sftp.mkdir(d)
        def cwd(self, d):
            self.sftp.chdir(d)
        def storbinary(self, cmd, file, blocksize = None):
            fn = cmd[5:]
            fp = self.sftp.open(fn, "w")
            shutil.copyfileobj(file, fp)
            fp.close()
        def chmod(self, fn, mode):
            self.sftp.chmod(fn, mode)
        def voidcmd(self, cmd):
            pass
        def login(self, user, pwd):
            self.transport.connect(username=user, password=pwd)
            self.sftp = paramiko.SFTPClient.from_transport(self.transport)
        def set_pasv(self, mode):
            pass
        def delete(self, fname):
            self.sftp.remove(fname)
        def quit(self):
            if self.transport:
                self.transport.close()
                self.transport = None

except ImportError:

    class SecureFTP:
        def __init__(self, hostname, port = 22):
            raise NotImplementedError("Secure Login Not Available - paramiko not found.")


##########################################################################
#  Set Variables
##########################################################################

user = ""
pwd = ""
host = ""
directory = ""
source = ""
passive = 0
chmod = 0
mode = "ftp"
zipf = None
lowername = 0
secure = None

rc = 0

##########################################################################
#  Process command line options
##########################################################################

import getopt

(optlist, args) = getopt.getopt(sys.argv[1:], "qvpt", \
    [ "quiet", "verbose", "touch", "pause", "zip=" ])

usage = "Usage: publish [ --quiet ] [ --verbose ] [ --touch ] [ --zip filename ] [ --pause ]\n"

verbose = 0
pause = 0

for i in optlist:
    if i[0] == '--touch' or i[0] == '-t':
        mode = "touch"
    elif i[0] == '--pause' or i[0] == '-p':
        pause = 1
    elif i[0] == '--verbose' or i[0] == '-v':
        verbose = 1
    elif i[0] == '--quiet' or i[0] == '-q':
        verbose = -1
    elif i[0] == '--zip':
        zipf = i[1]
        mode = "zip"
    else:
        sys.stderr.write(usage)
        sys.exit(1)

##########################################################################
#  Load the .site file
##########################################################################

if not os.path.isfile("./.site"):
    if os.path.isfile("../.site"):
        os.chdir("..")

try:
    execfile("./.site")
except:
    sys.stderr.write("Can't Execute Site File ./.site\n")
    import traceback
    traceback.print_exc(file = sys.stderr)
    if pause:
        raw_input("\nPress ENTER to Continue... ")
    sys.exit(1)

##########################################################################
#  Imports
##########################################################################

from ftplib import FTP, error_temp
import glob, os.path, string


##########################################################################
#  Global Variables
##########################################################################

stack = []

uploads = 0
deletes = 0
touches = 0


##########################################################################
#  Functions
##########################################################################

def publish(path, ftp, leader, mode):
    global stack, uploads, deletes, touches

    d = os.path.basename(path)
    if verbose >= 0:
        print leader + "publishing directory " + d

    stack.append(os.getcwd())
    os.chdir(d)

    if d[:1] == '%':
        d = d[1:]

    try:
        ftp.mkd(d)
    except:
        pass

    ftp.cwd(d)

    dirlist = glob.glob("*")
    dirlist.sort()

    for n in dirlist:

        if n == "RCS":
            continue

        key = path + "/" + n
        t = n
        if t[:1] == "%":
            t = t[1:]
        if lowername:
            t = t.lower()

        if os.path.isdir(n):
            publish(key, ftp, leader+" ", mode)
        else:
            if index.has_key(key):
                oldstamp = index[key][0]
            else:
                oldstamp = 0

            newstamp = os.stat(n)[8]

            if mode == "touch":
                if verbose >= 0:
                    print leader + "touching " + n
                touches += 1
            else:
                if newstamp != oldstamp:
                    if verbose >= 0:
                        print leader + "storing  " + n + " --> " + t
                    fp = open(n, "rb")
                    try:
                        ftp.storbinary("STOR " + t, fp, 1024)
                    except error_temp:
                        # try again, one time.
                        ftp.storbinary("STOR " + t, fp, 1024)
                    fp.close()
                    if chmod:
                        mode = os.stat(n)[0] & 0777
                        if hasattr(ftp, "chmod"):
                            ftp.chmod(t, mode)
                        else:
                            ftp.voidcmd("SITE CHMOD " + oct(mode) + " " + t)
                    uploads += 1
                elif verbose > 0:
                    print leader + "skipping " + n

            index[key] = [ newstamp, 1 ]

    if d != ".":
        os.chdir(stack.pop())
        ftp.cwd("..")

### main body ###

try:
    if source:
        if verbose >= 0:
            print "changing local directory to " + source
        os.chdir(source)

    # load the index

    index = {}

    if zipf is None:
        try:
            fp = open("./.index", "r")
            indexdata = fp.read()
            fp.close()
            index = eval(indexdata)
        except:
            pass

    if mode == "touch":
        ftp = NullFTP()
    elif mode == "zip":
        ftp = ZipFTP(zipf)
    elif mode == "copy":
        ftp = CopyFTP()
    elif secure:
        if verbose >= 0:
            print "secure login to " + host
        ftp = SecureFTP(host)
    else:
        if verbose >= 0:
            print "logging on to " + host
        ftp = FTP(host)

    ftp.login(user, pwd)

    ftp.set_pasv(passive)

    if mode != "zip":
        if verbose >= 0:
            print "set directory to " + directory
        try:
            ftp.mkd(directory)
        except:
            pass
        ftp.cwd(directory)

    publish(".", ftp, " ", mode)

    if not zipf:
        if verbose >= 0:
            print "removing outdated files"
        for i in index.keys():
            if len(index[i]) < 2:
                if verbose >= 0:
                    print "removing", i
                try:
                    ftp.delete(i)
                except:
                    pass
                del index[i]
                deletes += 1
            else:
                index[i] = index[i][:1]

    if verbose >= 0:
        print "done."

    if uploads > 0:
        print "uploaded %d" % uploads

    if touches > 0:
        print "touched %d" % touches

    if deletes > 0:
        print "deleted %d" % deletes

    ftp.quit()

except:
    import traceback
    traceback.print_exc(file = sys.stdout)

    # rewind

    while stack:
        os.chdir(stack.pop())

    rc = 1

if mode != "zip":
    print "saving .index"
    fp = open("./.index", "w")
    fp.write(repr(index))
    fp.close()

if pause:
    raw_input("\nPress ENTER to Continue... ")

sys.exit(rc)

# end of script.
