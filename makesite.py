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

"""makesite.py - build html files from source (.src) files

With no options, makesite.py reads in the file template.site from
the current directory, and then reads in each file with the source
extension (default .src) and creates a page combining the template.site
file and the source file, saving the result with a .html extension.

Both the source files and the template file are in a form similar to
rfc822 messages, that is, headers, a blank line, and a body.  The headers
are read in with my QChunk module, which is required to run this program.

The template file contains "magic comments" of the form:

    <!--%name%-->

where name is a macro to be substituted.

Basically, the template file is processed line by line.  Whenever one or
more magic comments are found, they are substituted with the information
from the source document header.  The magic comment "<!--%body%-->" is 
replaced with the source document body.

If a magic comment name can't be found in the source document, it is 
searched for in the template, and then in a special builtin "Chunk" 
which at present contains one entry, "date", containing today's date.

Command-line arguments may override default settings; the usage is as
follows:

    makesite.py [ --template=file ] [ --dir=directory ] [ filename ...]

--template overrides the default template file, template.site.
--dir specifies a directory to change to before processing begins.

Filename options, if given, indicate that only the named source files
are to be processed, rather than searching for them.  This is handy
when combining makesite.py and make.

The following template file headers also override default values:

    Target:    indicates that output files are to be put 
               in a different directory.
    Extension: provides a different file extension for 
               source files.  Don't include the dot (.)
               at the beginning of the extension.
               May include a second extension, separated
               by a space, for the target file extension
               (defaults to html)

"""

# my version numbers are usually strings
__version__ = "1.4"

######################################################################
# module imports
######################################################################

import glob, re, string, sys, getopt, os, QChunk, time, stat

######################################################################
# class and function definitions
######################################################################

Macro = re.compile(r'<!--%(.*?)%-->')

def_ctx = QChunk.Chunk()
def_ctx["Date"] = time.strftime("%m/%d/%Y", time.localtime(time.time()))
def_ctx["SrcDate"] = ""

class Record:
    pass

def stampof(fn):
    try:
        return os.stat(fn)[stat.ST_MTIME]
    except:
        return 0

def LoadTemplate(template_file):
    t_in = open(template_file, "r")
    tmpl = Record()
    tmpl.headers = QChunk.Chunk(t_in)
    tmpl.body = t_in.readlines()
    tmpl.stamp = stampof(template_file)
    t_in.close()
    return tmpl

def Process(lines, out, pri_ctx, alt_ctx):
    for line in lines:
        while line:
            mo = Macro.search(line)
            if mo:
                key = mo.group(1)
                out.write(line[:mo.start()])
                if string.lower(key) == "body":
                    Process(pri_ctx.body, out, alt_ctx, pri_ctx)
                else:
                    if pri_ctx.headers.has_key(key):
                        Process(pri_ctx.headers[key], out, alt_ctx, pri_ctx)
                    elif alt_ctx.headers.has_key(key):
                        Process(alt_ctx.headers[key], out, alt_ctx, pri_ctx)
                    elif alt_ctx.headers.has_key("def" + key):
                        Process(alt_ctx.headers["def"+key], out, \
                            alt_ctx, pri_ctx)
                    elif def_ctx.has_key(key):
                        Process(def_ctx[key], out, alt_ctx, pri_ctx)
                    elif verbose:
                        print "WARNING-- missing key <%s>" % key
                line = line[mo.end():]
            else:
                out.write(line)
                line = ''

def MakeSite(tmpl, filename):

    try:
        ext = tmpl.headers["Extension"]
    except KeyError:
        ext = "src"

    extl = string.split(ext)
    if len(extl) > 1:
        ext = extl[0]
        tgtext = extl[1]
    else:
        tgtext = "html"

    if filename and filename[-1 * len(ext):] != ext:
        ext = ""

    try:
        target = tmpl.headers["Target"]
    except KeyError:
        target = "./" 

    if filename:
        files = [ filename ]
    else:
        files = glob.glob("*." + ext)

    for infile in files:

        outfile = target + infile[:-1 * len(ext)] + tgtext

        msg = Record()

        msg.stamp = stampof(infile)
        tstamp = stampof(outfile)

        if not force and tstamp > max(msg.stamp, tmpl.stamp):
            if verbose:
                print "*** skipping", infile
            continue

        print infile, "->", outfile

        def_ctx["SrcDate"] = time.strftime("%m/%d/%Y", \
            time.localtime(os.stat(infile)[stat.ST_MTIME]))

        f_in = open(infile, "r")
        msg.headers = QChunk.Chunk(f_in)
        msg.body = f_in.readlines()
        f_in.close()

        f_out = open(outfile, "w")

        Process(tmpl.body, f_out, msg, tmpl)

        f_out.close()

######################################################################
# main body
######################################################################

if __name__ == '__main__':

    (optlist, args) = getopt.getopt(sys.argv[1:], "fvpt:d:", \
        [ "template=", "dir=", "pause", "force", "verbose" ])
    
    usage = "Usage: makesite [ options ] [ filename...]\n\n" + \
            "Options: --template=file\n" + \
            "         --dir=directory\n" + \
            "         --pause\n" + \
            "         --verbose\n" + \
            "         --force\n"
    
    template_file = "template.site"
    directory = ""
    pause = 0
    force = 0
    verbose = 0
    
    for i in optlist:
        if i[0] == '--template' or i[0] == '-t':
            template_file = i[1]
        elif i[0] == '--dir' or i[0] == '-d':
            directory = i[1]
        elif i[0] == '--pause' or i[0] == '-p':
            pause = 1
        elif i[0] == '--force' or i[0] == '-f':
            force = 1
        elif i[0] == '--verbose' or i[0] == '-v':
            verbose = 1
        else:
            sys.stderr.write(usage)
            sys.exit(1)
    
    if directory:
        if verbose:
            print "change directory to", directory
        os.chdir(directory)
    
    tmpl = LoadTemplate(template_file)
    
    if len(args) > 0:
        for i in args:
            MakeSite(tmpl, i)
    else:
        MakeSite(tmpl, None)
    
    if pause:
        raw_input("\nPress ENTER to Continue... ")
    
######################################################################
