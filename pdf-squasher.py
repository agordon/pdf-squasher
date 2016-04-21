#!/usr/bin/env python

"""
PDF Squasher
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

import os,sys,argparse, re, shutil
from subprocess import call, check_call, CalledProcessError
from tempfile import mkdtemp
import os.path
from os.path import basename


version_info=\
"""
PDF Squasher - version 0.2
Copyright (C) 2016 Assaf Gordon <assafgordon@gmail.com>
License: GPLv3-or-later
"""

distance_epsilon=0.005
verbose=False


def parse_command_line():
    # Define parameters
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=version_info,
        version=version_info,
        epilog="""

Example:

read 'input.pdf', try to reduce the output size by merging
rectangle objects:

    $ %(prog)s -o output.pdf input.pdf

Same as above, but write intermediate output files to 'FOO'
directory, for debugging/troubleshooting:

    $ %(prog)s --outdir foo input.pdf

        """)


    # Option parameters
    parser.add_argument("--verbose",  help="be verbose",
                        action="store_true")
    parser.add_argument("--distance-epsilon",type=float,default=0.005,
                        metavar="E",
                        help="distance epsilon: rectangles closer than this "\
                             "value (in PDF coordinates) will be merged. " \
                             "Larger values might produce small PDF files " \
                             "(default: %(default)f).")

    parser.add_argument("--output", "-o", metavar="FILE", action="store",
                        dest="output_filename", help="output PDF file")
    parser.add_argument("--outdir", metavar="DIR",action="store",
                        dest="output_directory",
                        help="write intermediate output files to this directory,"\
                             "and don't delete it after completion")

    # Positional parameter
    parser.add_argument('filename', metavar='FILE', help='PDF file to process');
    args = parser.parse_args()


    if not args.output_filename and not args.output_directory:
        # without one of these - the output will be lost...
        # TODO: perhaps print to STDOUT ?
        sys.exit("usage error: missing --output or --outdir (or both)")


    return args



def decompress_pdf(infile,outfile):
    """
    Pre-process a PDF file, prepare it for text-manipulation.
    PDF files can contain binary and/or compressed streams.
    'mutool' (part of 'mupdf' package) will decompress (-d)
    and hex-encode (-a) these streams.

    The output PDF file should be equivalent to the input
    (i.e. identical rendering), but should contain no binary data
    and no compressed data, and thus much easier to text-process.
    """
    cmd = [ 'mutool', 'clean', '-a', '-d', infile, outfile ]
    try:
        check_call(cmd)
    except CalledProcessError as e:
        sys.exit("mutool failed, returned code %d" % (e.returncode))
    except OSError as e:
        sys.exit("failed to execute 'mutool': '%s' (is mupdf package " \
                 "installed?)" % (str(e)))


def compress_pdf(infile,outfile):
    """
    Post-process a PDF file, compress its streams thus reducing the file size.
    'qpdf' is part of the 'qpdf' package.

    NOTE:
    The input PDF file might have some invalid streams (artifact of 'mutool'
    extractions). QPDF can fix some/most of them (and will exit with code 3).

    TODO: fix this mess.
    """
    cmd = [ 'qpdf', '--stream-data=compress', infile, outfile ]
    try:
        rc = call(cmd)
        if rc != 0 and rc != 3:
            sys.exit("QPDF failed, exit code %d (input: '%s' output: '%s')" % \
                     (rc, infile,outfile))
    except OSError as e:
        sys.exit("failed to execute 'qpdf': '%s' (is qpdf package " \
                 "installed?)" % (str(e)))


def merge_pdf_re_f(infile,outfile):
    """
    This function processes an uncompressed PDF stream,
    and merges lines of 're' and 'f' into one
    (simplifying downstream processing).

    Example:
    PDF input (of decompressed stream):

       1420.1 4710.9 159.598 101.902 re
       f
       1420.1 4812.8 159.598 101.898 re
       f
       1420.1 4914.6 159.598 101.898 re
       f

    Output:

       1420.1 4710.9 159.598 101.902 re f
       1420.1 4812.8 159.598 101.898 re f
       1420.1 4914.6 159.598 101.898 re f

    Nothing else is changed.

    NOTES:
    1. No input validation.
    2. Input must not have binary data (use 'mutool -a -d' beforehand)
    """
    try:
        inf = open(infile,'r')
        outf = open(outfile,'w')

        prev = ""
        for line in inf:
            line = line.strip()

            if line == "f" and prev.endswith(" re"):
                print >>outf, prev + " f"
                prev = ""
                continue

            if prev:
                print >>outf, prev

            prev = line

        inf.close()
        outf.close()
    except IOError as e:
        # Ugly, unsafe hack: str(e) should include the offending filename.
        # (otherwise, this error message is useless)
        sys.exit("I/O error: %s" % (str(e)))



def parse_pdf_re_f(line):
    """
    current implementation accepts a single format:
       X Y W H re f

    This function parses such a textline,
    and returns a dictionary of x,y,w,h
    or None if the line is not in recognizable format.

    Example:
      > d = parse_pdf_re_f("1 2 3 4 re f")
      > print d
      { 'x': 1, 'y': 2, 'w': 3, 'h': 4 }

    """
    parts = line.strip().split(' ')
    if len(parts)!=6:
        return None

    try:
        x = float(parts[0])
        y = float(parts[1])
        w = float(parts[2])
        h = float(parts[3])
    except ValueError as e:
        return None

    if not (parts[4] == "re"):
        return None
    if not (parts[5] == "f"):
        return None

    return {'x':x, 'y':y, 'w':w ,'h': h}



def can_merge_horizontally(r1,r2):
    # Same row and height
    if r1['y'] != r2['y'] or r1['h'] != r2['h']:
        return False;

    # And similar enough distance (rects adjacent or overlap)
    if r1['x'] + r1['w'] + distance_epsilon >= r2['x']:
        return True

    return False


def can_merge_vertically(r1,r2):
    # Same column and width
    if r1['x'] != r2['x'] or r1['w'] != r2['w']:
        return False;

    # And similar enough distance (rects adjacent or overlap)
    if r1['y'] + r1['h'] + distance_epsilon >= r2['y']:
        return True

    return False


def merge_horizontally(r1,r2):
    d = { 'x': r1['x'],
          'y': r1['y'],
          'w': max(r1['w'],r1['w']+r2['w']),
          'h': r1['h'] }
    return d



def merge_vertically(r1,r2):
    d = { 'x': r1['x'],
          'y': r1['y'],
          'w': r1['w'],
          'h': max(r1['h'],r1['h'] + r2['h']) }
    return d



def process_rectangles(rects,outf):
    if len(rects)==0:
        return

    s = sorted(rects, key=lambda item: (item['x'], item['y']))

    if verbose:
        print >>outf,"% "
        print >>outf,"% unsorted rectnagles:"
        for i in rects:
            print >>outf,"%% %f %f %f %f re f" % (i['x'], i['y'], i['w'], i['h'])

        print >>outf,"% "
        print >>outf,"% sorted rectanges:"
        for i in s:
            print >>outf,"%% %f %f %f %f re f" % (i['x'], i['y'], i['w'], i['h'])


    out = []
    prev = s.pop(0)
    for i in s:
        if not prev:
            prev = i
            continue

        if can_merge_horizontally(prev,i):
            prev = merge_horizontally(prev,i)
        elif can_merge_vertically(prev,i):
            prev = merge_vertically(prev,i)
        else:
            out.append(prev)
            prev = None
    if prev:
        out.append(prev)

    if verbose:
        print >>outf,"% "
        print >>outf,"% merged rectanges:"

    for i in out:
        print >>outf,"%f %f %f %f re f" % (i['x'], i['y'], i['w'], i['h'])




def merge_pdf_rectangles(infile,outfile):
    rectangles = []

    try:
        inf = open(infile,'r')
        outf = open(outfile,'w')

        for linenum,line in enumerate(inf):
            err = "input error at %s line %d" % (infile, linenum+1)
            line = line.rstrip()

            # Not a rectangle line - print and continue
            if not line.endswith(" re f"):
                process_rectangles(rectangles,outf)
                rectangles = []
                print >>outf, line
                continue

            # Process rectangle line
            d = parse_pdf_re_f(line)

            # Invalid rectangle line - print and continue
            if not d:
                if verbose:
                    msg = "%s line %d: skipped re/f line with unrecognized"\
                          " format (%s)" % (infile, linenum+1, line)
                    print >>sys.stderr,msg

                process_rectangles(rectangles,outf)
                rectangles = []
                print >>outf,line

            # Valid rectangle line - save for later processing
            rectangles.append(d)

        # process any remaining rectangles (highly unlikely, as that would
        # indicate a broken PDF stream)
        process_rectangles(rectangles,outf)

        inf.close()
        outf.close()
    except IOError as e:
        # Ugly, unsafe hack: str(e) should include the offending filename.
        # (otherwise, this error message is useless)
        sys.exit("I/O error: %s" % (str(e)))




if __name__ == "__main__":
    args = parse_command_line()

    verbose = args.verbose
    distance_epsilon = args.distance_epsilon

    if not os.path.isfile(args.filename):
        sys.exit("input file '%s' not found (or not a regular file)" \
                 % args.filename)

    # Set output directory
    if args.output_directory:
        tmpdir = args.output_directory
        try:
            os.makedirs(tmpdir)
        except OSError as e:
            sys.exit("failed to create output directory '%s': %s" % (tmpdir,str(e)))
    else:
        tmpdir = mkdtemp('.pdf-shrink-rectangles')

    ##
    ## PDF processing pipeline
    ##
    base = os.path.splitext(basename(args.filename))

    ##
    ## Decompress streams in PDF file
    ##
    decomp_pdf_filename = os.path.join(tmpdir,"decompressed.pdf")
    decompress_pdf(args.filename, decomp_pdf_filename)

    ##
    ## Merge RE/F lines into one 'X Y W H re f' lines.
    ##
    re_f_merged_pdf_filename = os.path.join(tmpdir,"merged-re-f.pdf")
    merge_pdf_re_f(decomp_pdf_filename, re_f_merged_pdf_filename)


    ##
    ## Merge overlapping/adjacent rectangles of identical colors
    ##
    merged_rect_pdf_filename = os.path.join(tmpdir,"merged-rects.pdf")
    merge_pdf_rectangles(re_f_merged_pdf_filename, merged_rect_pdf_filename)

    ##
    ## Compress PDF (generate binary,compressed streams) to reduce file size
    ##
    comp_pdf_filename = os.path.join(tmpdir,"final.pdf")
    compress_pdf(merged_rect_pdf_filename, comp_pdf_filename)

    ##
    ## Final Output
    ##
    if args.output_filename:
        # Copy the final output PDF file to the user's requested location
        shutil.copy2(comp_pdf_filename,args.output_filename)

    if not args.output_directory:
        # user doesn't want to keep output directory, delete it.
        shutil.rmtree(tmpdir)
