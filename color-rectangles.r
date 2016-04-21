#!/usr/bin/env Rscript

# PDF Squasher - demo plot script
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
# along with this program  If not, see <http://www.gnu.org/licenses/>.



# This script generates a plot with 100 lines, each in a different color,
# for each line, draw 1000 tiny adjacent rectangles forming a horizontal line.
#
# The resulting PDF will will have 100,000 rectangle objects,
# making PDF viewing slow and PDF manipulation quite frustrating
# (e.g in Adobe Illustrator / Inkscape).
#
# This is a contrived example of a common-scenario:
# a data plot contains many objects (points/lines/rectangles)
# originating from a large dataset.

pdf("color-rectangles.pdf")

plot(c(0,100),c(0,100) , type = "n",  xlab = "", ylab = "",)

i = 0:999
c = rainbow(100)

for (y in 0:99) {
  rect(
        i/10, y,            # left,top corner
        i/10 + 0.11, y+1,   # right,bottom corner
        col=c[y],           # color (same for all rectangles in a line)
        lwd=0,lty="blank"   # fill, but no border line
      )
}
