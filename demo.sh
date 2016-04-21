#!/bin/sh

# PDF Squasher - demo script
# Copyright (C) 2016 Assaf Gordon (assafgordon@gmail.com)
#
# PDF Squasher is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.



# Cleanup previous runs (if any)
rm -rf color-rectanges.pdf color-rectangles-small.pdf color-rectangles

##
## Generate the plot
##
./color-rectangles.r

##
## Merge the PDF rectangles
##


./pdf-squasher.py --output color-rectangles-squashed.pdf \
                  --outdir color-rectangles/ \
                  color-rectangles.pdf

##
## Show results
##
echo
echo

echo "PDF plot before squashing:"
echo
ls -lh color-rectangles.pdf | sed 's/^/    /'
echo

echo "Uncompressed PDF plot before squashing:"
echo
ls -lh color-rectangles/decompressed.pdf | sed 's/^/    /'
echo

echo "Uncompressed PDF plot after squashing:"
echo
ls -lh color-rectangles/merged-rects.pdf | sed 's/^/    /'
echo

echo
echo "Compressed PDF plot after squashing:"
echo
ls -lh color-rectangles-squashed.pdf | sed 's/^/    /'
echo
echo
echo "now open the two files in a PDF viewer and "
echo "examine the plots for any differences."
