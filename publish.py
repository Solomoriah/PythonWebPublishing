#!/usr/bin/env python
#
# Software License
# 
# The majority of my software is published under a BSD-style license,
# given below.  Please check the specific package you downloaded to
# be sure that this license applies.
# 
# Copyright &copy; 2001, Chris Gonnerman
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

publish.py publishes only pages that have changed sizes.  This means that
sometimes a page that should be published won't be; if it is an HTML page
you can just:

    echo >>filename.html

to add a blank line at the end and force the file to publish.
"""

# my version numbers are usually strings
__version__ = "1.4"

import os, sys

##########################################################################
#  NullFTP is used by the touch function
##########################################################################

class NullFTP:
    def nullfunc(self, *args):
        pass
    def __getattr__(self, attr):
        return self.nullfunc

##########################################################################
#  Load the .site file
##########################################################################

user = ""
pwd = ""
host = ""
directory = ""
source = ""
passive = 0

if not os.path.isfile("./.site"):
    if os.path.isfile("../.site"):
        os.chdir("..")

try:
    execfile("./.site")
except:
    sys.stderr.write("Can't Execute Site File ./.site\n")
    sys.exit(1)

##########################################################################
#  Load the .index file
#
#  .index should contain a valid repr() of a dictionary, where the
#  keys are filenames and the values are lists containing the timestamps,
#  as returned as element 8 of the stat tuple.  The values have to be
#  stored in lists because we will be storing a temporary flag there.
#  
#  .index won't be found the first time through.
##########################################################################

try:
    fp = open("./.index", "r")
    indexdata = fp.read()
    fp.close()
    index = eval(indexdata)
except:
    index = {}

import getopt

(optlist, args) = getopt.getopt(sys.argv[1:], "pt", \
    [ "touch", "pause" ])

usage = "Usage: publish [ --touch ] [ --pause ]\n"

touch = 0
pause = 0

for i in optlist:
    if i[0] == '--touch' or i[0] == '-t':
        touch = 1
    elif i[0] == '--pause' or i[0] == '-p':
        pause = 1
    else:
        sys.stderr.write(usage)
        sys.exit(1)

##########################################################################
#  Imports
##########################################################################

from ftplib import FTP
import glob, os.path, string

def publish(path, ftp, leader, touch):
    d = os.path.basename(path)
    print leader + "publishing directory " + d
    os.chdir(d)
    if d[:1] == '%':
        d = d[1:]
    try:
        ftp.mkd(d)
    except:
        pass
    ftp.cwd(d)

    for n in glob.glob("*"):

        if n == "RCS":
            continue

        key = path + "/" + n
        t = n
        if t[:1] == "%":
            t = t[1:]

        if os.path.isdir(n):
            publish(key, ftp, leader+" ", touch)
        else:
            if index.has_key(key):
                oldstamp = index[key][0]
            else:
                oldstamp = 0

            newstamp = os.stat(n)[8]

            index[key] = [ newstamp, 1 ]

            if touch:
                print leader + "touching " + n
            else:
                if newstamp != oldstamp:
                    print leader + "storing  " + n + " --> " + t
                    fp = open(n, "rb")
                    ftp.storbinary("STOR " + t, fp, 1024)
                    fp.close()
                else:
                    print leader + "skipping " + n

    if d != ".":
        os.chdir("..")
    ftp.cwd("..")

if source:
    print "changing local directory to " + source
    os.chdir(source)

print "logging on to " + host

if touch:
    ftp = NullFTP()
else:
    ftp = FTP(host)

ftp.login(user, pwd)

ftp.set_pasv(passive)

print "set directory to " + directory

try:
    ftp.mkd(directory)
except:
    pass

ftp.cwd(directory)

publish(".", ftp, " ", touch)

print "removing outdated files"
ftp.cwd(directory)
for i in index.keys():
    if len(index[i]) < 2:
        print "removing", i
        try:
            ftp.delete(i)
        except:
            pass
        del index[i]
    else:
        index[i] = index[i][:1]

print "saving .index"

fp = open("./.index", "w")
fp.write(repr(index))
fp.close()

print "done."

ftp.quit()

if pause:
    raw_input("\nPress ENTER to Continue... ")

# end of script.
