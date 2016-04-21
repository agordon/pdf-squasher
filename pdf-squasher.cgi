#!/usr/bin/env python

"""
PDF Squasher - CGI runner script
Copyright (C) 2016 Assaf Gordon (assafgordon@gmail.com)

PDF Squasher is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""
This is the CGI script which runs the online pdf squasher
web-page: http://agordon.github.io/pdf-squasher
cgi-bin:  http://scripts.housegordon.org/cgi-bin/pdf-squasher.cgi
"""

import cgi
#import cgitb; cgitb.enable()  # for troubleshooting
from tempfile import NamedTemporaryFile
from subprocess import check_output, CalledProcessError, STDOUT
import sys,os,shutil
from resource import RLIMIT_NOFILE,RLIMIT_DATA,RLIMIT_CPU,RLIMIT_FSIZE,\
                     setrlimit


def http_error(http_code,http_status,msg):
    print """Status: %d %s
Content-type: text/plain

%s""" % ( int(http_code), str(http_status), str(msg) )
    print >>sys.stderr,"returned HTTP error %d (%s): %s" \
        % (int(http_code), str(http_status), str(msg))
    sys.exit(0)

def http_bad_request_error(msg):
    http_error(400,"Bad Request",msg)

def http_server_error(msg):
    http_error(500,"Internal Server Error",msg)


def save_cgi_file_param(form,var_name):
    if not var_name in form:
        msg = "missing CGI file parameter '%s'" % (var_name)
        http_bad_request_error(msg)

    f = form[var_name]
    if not f.file:
        msg = "invalid '%s' parameter (expecting file-upload)" % (var_name)
        http_server_error(msg)

    local_fn=""
    try:
        outf = NamedTemporaryFile(suffix='.input.pdf',delete=False)
        local_fn = outf.name
        while 1:
            chunk = f.file.read(100000)
            if not chunk: break
            outf.write (chunk)
        outf.close()
    except IOError as e:
        http_server_error("I/O error: %s" % (str(e)))
    except OSError as e:
        http_server_error("OS error: %s" % (str(e)))

    return local_fn


def run_pdf_squasher(pdf_in,pdf_out,epsilon):
    cmd = ["pdf-squasher.py",
           "--distance-epsilon",str(float(epsilon)),
           "-o",pdf_out,
           pdf_in ]

    msg = ' '.join(cmd)
    print >>sys.stderr,"executing:", msg

    try:
        output = check_output(cmd,shell=False)
    except OSError as e:
        http_server_error("failed to execute pdf-squasher.py: %s" % (str(e)))
    except CalledProcessError as e:
        http_server_error("pdf-squasher.py returned exit code %d (possibly invalid PDF file)" % \
                          e.returncode)


# Add some limits
setrlimit(RLIMIT_CPU, (15,15))
setrlimit(RLIMIT_FSIZE, (20000000,20000000))
setrlimit(RLIMIT_NOFILE, (50,50))
setrlimit(RLIMIT_DATA, (20000000,20000000))
os.nice(10)


form = cgi.FieldStorage()
pdf_input = save_cgi_file_param(form,'pdffile')
tmp = NamedTemporaryFile(suffix=".output.pdf",delete=False)
pdf_output = tmp.name
tmp.close()
run_pdf_squasher(pdf_input,pdf_output,0.5)

"""
print "Content-Type: text/plain"
print
print "inpit file: ", pdf_input
print "output file: ", pdf_output
"""

# Send the PDF back
print "Content-Type: application/pdf; charset=binary"
print "Content-disposition: attachment; filename=squashed.pdf"
print

# Send binary file to STDOUT
try:
    sys.stdout.flush()

    inf = open(pdf_output,'rb')
    while 1:
        chunk = inf.read(100000)
        if not chunk: break
        sys.stdout.write (chunk)
    inf.close()
except IOError as e:
    print >>sys.stderr,"failed to send binary data to stdout: %s" % (str(e))

# Delete the temporary files
os.unlink(pdf_input)
os.unlink(pdf_output)
