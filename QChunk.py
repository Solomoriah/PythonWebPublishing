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

"""QChunk.py -- Read, Save, and Handle 'Chunk-files'

A Chunkfile looks like this (without indentation):

    Key1: Value1
    Key2: Value2
    Key3::
    Value3
    Has
    Several
    Lines
    .

    Name: Chunk2
    Key1: Value1
    Key2: Value2

In long words:
    A Chunkfile contains zero or more Chunks.
    A Chunk is represented by Key: Value pairs.
    If a value contains newlines, the format is Key:: on one line,
        then data lines, followed by a single period in column 0.
    A blank line ends a Chunk.

This is similar to the header format of rfc822.Message; in fact, that was
my inspiration.

A Chunk loaded into memory looks like a dictionary; however the keys and
values are required to be strings, and key matches are done in case-
insensitive fashion.

The Chunk constructor accepts an optional file-like-object parameter, and
attempts to load the next Chunk from it.  With no parameters, the 
constructor returns an empty Chunk.

Chunkfiles may be loaded entirely into memory, or processed a Chunk at a
time.  There is a class provided, ChunkReader, which requires a file-like
object as an argument, and returns a reader object.

The reader object has one method, .next(), and one data member, .chunk.
Do this:

    r = ChunkReader(in_file)

No I/O is done yet.  When r.next() is called, the first Chunk is read, 
and 1 is returned; if there are no Chunks left when r.next() is called,
None is returned.  You can access the loaded Chunk through the r.chunk 
data member.
"""

__version__ = "1.1"

import UserDict
import string
import re

# exceptions
class Error:
    def __init__(self, msg):
        self.msg = msg
    def __repr__(self):
        return repr(self.msg)
    def __str__(self):
        return str(self.msg)

class DataError(Error):
    pass

class Chunk(UserDict.UserDict):

    __multi_target = re.compile(r"([^:][^:]*):: *$")
    __target = re.compile(r"([^:][^:]*): *(.*) *")
    __blank_target = re.compile(r" *\n$")

    def __init__(self, file = None):
        UserDict.UserDict.__init__(self)
        if file != None:
            line = file.readline()
            # rip off blank lines
            #while line == "\n":
            while self.__blank_target.match(line):
                line = file.readline()
            while line and not self.__blank_target.match(line):
                line = line[:-1]
                mo = self.__multi_target.match(line)
                if mo:
                    l = ""
                    line = file.readline()
                    while line and line != ".\n":
                        l = l + line
                        line = file.readline()
                    if not line:
                        raise IOError, "unexpected eof on input"
                    # remove a newline on input
                    l = l[:-1]
                    UserDict.UserDict.__setitem__(self, string.lower(mo.group(1)), l)
                else:
                    mo = self.__target.match(line)
                    if not mo:
                        raise DataError, "data error on input: " + `line`
                    UserDict.UserDict.__setitem__(self, string.lower(mo.group(1)), mo.group(2))
                line = file.readline()

    def Save(self, file):
        k = UserDict.UserDict.keys(self)
        k.sort()
        for i in k:
            if string.find(self[i], "\n") != -1:
                file.write(i + "::\n")
                # add a newline on output
                file.write(self[i] + "\n")
                file.write(".\n")
            else:
                file.write(i + ": " + self[i] + "\n")
        file.write("\n")

    def __getitem__(self, key):
        if type(key) != type(""):
            raise TypeError, "invalid key type"
        return UserDict.UserDict.__getitem__(self, string.lower(key))

    def __setitem__(self, key, value):
        if type(key) != type(""):
            raise TypeError, "invalid key type"
        if type(value) != type(""):
            raise TypeError, "invalid value type"
        return UserDict.UserDict.__setitem__(self, string.lower(key), value)

    def __delitem__(self, key):
        if type(key) != type(""):
            raise TypeError, "invalid key type"
        return UserDict.UserDict.__setitem__(self, string.lower(key), value)

    def has_key(self, key):
        if type(key) != type(""):
            raise TypeError, "invalid key type"
        return UserDict.UserDict.has_key(self, string.lower(key))

    def get(self, key, default):
        if type(key) != type(""):
            raise TypeError, "invalid key type"
        if type(default) != type(""):
            raise TypeError, "invalid default type"
        if UserDict.UserDict.has_key(self, string.lower(key)):
            return UserDict.UserDict.__getitem__(self, string.lower(key))
        return default

class ChunkReader:
    def __init__(self, file):
        self.file = file
    def next(self):
        self.chunk = Chunk(self.file)
        if self.chunk:
            return 1
        return None

# end of script.
