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

With no options, makesite.py reads in the file(s) template.* from
the current directory, and then reads in each file with the source
extension (default .src) and creates a page combining the template.*
file(s) and the source file, saving the result with a .html extension.

Both the source files and the template file are in a form similar to
rfc822 messages, that is, headers, a blank line, and a body.  The headers
are no longer read in using my QChunk module, but the header format hasn't
changed.

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

--template overrides the default template file pattern, "template.*".
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

This version is also the first to support dynamic generation.  It goes
like this:

    import makesite

    tmpl = makesite.Template()                # to get a blank template,
                                              # then fill it in, OR do
    tmpl = makesite.LoadTemplate("filename")  # THIS to load a saved 
                                              # template.
    fill = makesite.Template()                # fill in the macro values.

    res = tmpl * fill                         # generate the output 
                                              # document as a string.
    sys.stdout.write(res)                     # then send it to the 
                                              # browser.

I find this most useful with the saved template file; I can use the same
template for static generation of most of my site's pages and retain the
same look and feel on cgi-generated pages.

The Template class is a mapping, where keys must be strings.  Key lookups
are case insensitive.  In addition to the basic mapping calls, there is
a Load() method for loading a Template from a file-like object, and the
__add__() and __mul__() methods are overloaded.  Adding a template to a 
template, like so:

    res = tmpl1 + tmpl2

results in a copy of tmpl1 with values from tmpl2 added, only where tmpl1
doesn't already have the given key.  Multiplying templates, like so:

    res = tmpl1 * tmpl2

returns a string which is the result of applying the source file (tmpl2)
to the template file (tmpl1) as given above.

When input filename begins with a $ (dollar sign) it will be removed
from the output filename.  This is handy for creating dotfiles.
"""

# my version numbers are usually strings
__version__ = "2.0"

######################################################################
# module imports
######################################################################

import glob, re, string, sys, getopt, os, time, stat, UserDict

######################################################################
# exceptions
######################################################################

class Error:
    def __init__(self, msg):
        self.msg = msg
    def __repr__(self):
        return repr(self.msg)
    def __str__(self):
        return str(self.msg)

class DataError(Error):
    pass


######################################################################
# class and function definitions
######################################################################

_verbose = None
_force = None
_pause = None
_directory = "."

class Generic:
    pass

Macro = re.compile(r'<!--%(.*?)%-->')
ExecMacro = re.compile(r'<!--!(.*?)!-->')

def stampof(file):
    try:
        return os.fstat(file.fileno())[stat.ST_MTIME]
    except:
        return 0

class Template(UserDict.UserDict):

    __multi_target = re.compile(r"([^:][^:]*):: *$")
    __target = re.compile(r"([^:][^:]*): *(.*) *")
    __blank_target = re.compile(r" *\n$")

    def __init__(self, file = None, mapping = None):
        UserDict.UserDict.__init__(self)
        if file is not None:
            self.Load(file)
        if mapping is not None:
            for k in mapping.keys():
                Template.__setitem__(self, k, str(mapping[k]))

    def Load(self, file):
        self["_stamp"] = stampof(file)
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
                self[string.lower(mo.group(1))] = l
            else:
                mo = self.__target.match(line)
                if not mo:
                    raise DataError, "data error on input: " + `line`
                self[string.lower(mo.group(1))] = mo.group(2)
            line = file.readline()
        # now we have the headers, let's get the body
        self["body"] = file.readlines()

    def Save(self, file):
        k = UserDict.UserDict.keys(self)
        k.sort()
        for i in k:
            if i != "body" and i[0:1] != "_":
                if string.find(self[i], "\n") != -1:
                    file.write(i + "::\n")
                    # add a newline on output
                    file.write(self[i] + "\n")
                    file.write(".\n")
                else:
                    file.write(i + ": " + self[i] + "\n")
        file.write("\n")
        file.write(string.join(self["body"],"\n"))

    def __getitem__(self, key):
        key = str(key)
        rc = UserDict.UserDict.__getitem__(self, string.lower(key))
        return rc

    def __setitem__(self, key, value):
        key = str(key)
        return UserDict.UserDict.__setitem__(self, string.lower(key), value)

    def __delitem__(self, key):
        key = str(key)
        return UserDict.UserDict.__setitem__(self, string.lower(key), value)

    def has_key(self, key):
        key = str(key)
        return UserDict.UserDict.has_key(self, string.lower(key))

    def get(self, key, default):
        key = str(key)
        try:
            rc = self.__getitem__(self, string.lower(key))
        except KeyError:
            rc = default
        return rc

    def __process(self, alt_ctx, lines, out, depth):
        if type(lines) is type(""):
            lines = [ lines ]
        if depth > 6:
            print "recursive definition error:", lines[0]
            return
        for line in lines:
            while line:
                mo = Macro.search(line)
                emo = ExecMacro.search(line)
                if mo and emo and emo.start() < mo.start():
                    mo = None
                if mo:
                    key = mo.group(1)
                    out.append(line[:mo.start()])
                    if alt_ctx.has_key(key):
                        alt_ctx.__process(self, alt_ctx[key], out, depth + 1)
                    elif self.has_key(key):
                        alt_ctx.__process(self, self[key], out, depth + 1)
                    elif alt_ctx.has_key("def" + key):
                        alt_ctx.__process(self, alt_ctx["def"+key], out, depth + 1)
                    elif _verbose:  ### fix this ugly hack
                        print "WARNING-- missing key <%s>" % key
                    line = line[mo.end():]
                elif emo:
                    key = emo.group(1)
                    out.append(line[:emo.start()])
                    try:
                        out.append(getattr(self["_module"], key)(self, alt_ctx))
                    except KeyError:
                        out.append(getattr(alt_ctx["_module"], key)(alt_ctx, self))
                    line = line[emo.end():]
                else:
                    out.append(line)
                    line = ''
        depth -= 1

    def __add__(self, other):
        # adding is defined strictly for applying defaults
        if not isinstance(other, Template):
            raise TypeError, 'can only "add" a Template to a Template'
        res = Template()
        for k in other.keys():
            res[k] = other[k]
        for k in self.keys():
            res[k] = self[k]
        return res

    def __mul__(self, other):
        if not isinstance(other, Template):
            raise TypeError, 'can only "multiply" a Template by a Template'
        lst = []
        self.__process(other, self["body"], lst, 0)
        return string.join(lst, "")


def LoadTemplate(template_file):
    try:
        t_in = open(template_file, "r")
    except:
        t_in = open("../" + template_file, "r")
    tmpl = Template(t_in)
    t_in.close()
    tmpl["_filename"] = template_file
    return tmpl


def defaultctx():
    try:
        def_ctx = LoadTemplate(".default")
    except:
        def_ctx = Template()
    
    def_ctx["Date"] = time.strftime("%m/%d/%Y", time.localtime(time.time()))
    def_ctx["SrcDate"] = ""

    return def_ctx


def _loadmodule(filename):
    mod = Generic()
    try:
        fp = open(module_file, "r")
        src = fp.read()
        fp.close()
        exec src in mod.__dict__
    except IOError:
        pass
    try:
        fp = open(filename, "r")
        src = fp.read()
        fp.close()
        exec src in mod.__dict__
    except IOError:
        pass
    return mod


def MakeSite(tmpl, filename):

    try:
        exts = tmpl["Extension"]
    except KeyError:
        exts = "src html py"

    extl = string.split(exts)

    ext, tgtext, modext = (extl + ([ None ] * 3))[:3]

    if not ext:
        ext = "src"

    if not tgtext:
        tgtext = "html"

    if not modext:
        modext = "py"

    ext = "." + ext
    tgtext = "." + tgtext
    modext = "." + modext

    if filename and filename[-1 * len(ext):] != ext:
        ext = ""

    try:
        target = tmpl["Target"]
    except KeyError:
        try:
            target = def_ctx["Target"]
        except KeyError:
            target = "./" 

    if filename:
        files = [ filename ]
    else:
        files = glob.glob("*" + ext)
        files.sort()

    for infile in files:

        rootname = infile[:-1 * len(ext)]

        outfile = rootname + tgtext
        if outfile[:1] == '$':
            outfile = outfile[1:]
        outfile = target + outfile

        msg = LoadTemplate(infile)

        mod = _loadmodule(rootname + modext)

        try:
            msg = mod._prefilter(msg)
        except AttributeError:
            pass

        msg["_module"] = mod

        try:
            fp = open(outfile, "r")
            tstamp = stampof(fp)
            fp.close()
        except:
            tstamp = 0

        if not _force and tstamp > max(msg["_stamp"], tmpl["_stamp"]):
            if _verbose:
                print "*** skipping", infile
            continue

        print infile, "->", outfile

        def_ctx["SrcDate"] = time.strftime("%m/%d/%Y", \
            time.localtime(os.stat(infile)[stat.ST_MTIME]))

        res = (tmpl + def_ctx) * msg

        f_out = open(outfile, "w")
        f_out.write(res)
        f_out.close()

######################################################################
# main body
######################################################################

if __name__ == '__main__':

    (optlist, args) = getopt.getopt(sys.argv[1:], "fnvpt:d:", \
        [ "template=", "module=", "dir=", "norc", "pause", "force", "verbose" ])
    
    usage = "Usage: makesite [ options ] [ filename...]\n\n" + \
            "Options: --template=file\n" + \
            "         --module=file\n" + \
            "         --dir=directory\n" + \
            "         --pause\n" + \
            "         --verbose\n" + \
            "         --force\n" + \
            "         --norc\n"
    
    template_file = "template.*"
    module_file = "module.site"

    _directory = ""
    _pause = 0
    _force = 0
    _verbose = 0
    _norc = 0
    
    for i in optlist:
        if i[0] == '--template' or i[0] == '-t':
            template_file = i[1]
        elif i[0] == '--module':
            module_file = i[1]
        elif i[0] == '--dir' or i[0] == '-d':
            _directory = i[1]
        elif i[0] == '--pause' or i[0] == '-p':
            _pause = 1
        elif i[0] == '--force' or i[0] == '-f':
            force = 1
        elif i[0] == '--verbose' or i[0] == '-v':
            _verbose = 1
        elif i[0] == '--norc' or i[0] == '-n':
            _norc = 1
        else:
            sys.stderr.write("\nArgument [%s] Not Recognized.\n\n" % i[0])
            sys.stderr.write(usage)
            sys.exit(1)
    
    if _directory:
        if _verbose:
            print "change directory to", _directory
        os.chdir(_directory)
    
    if not _norc and os.path.exists(".makesite"):
        if _verbose:
            print "running .makesite"
        fp = open(".makesite", "r")
        script = fp.read()
        fp.close()
        exec script in {}

    def_ctx = defaultctx()

    template_files = glob.glob(template_file)

    for t in template_files:
        print "Processing Template", t

        tmpl = LoadTemplate(t)

        if len(args) > 0:
            for i in args:
                MakeSite(tmpl, i)
        else:
            MakeSite(tmpl, None)
    
    if _pause:
        raw_input("\nPress ENTER to Continue... ")
    
######################################################################
