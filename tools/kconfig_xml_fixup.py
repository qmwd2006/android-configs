#!/usr/bin/env python

from __future__ import print_function
import os
import re
import sys

def fixup(arg):
    source_f = open(arg) or die ("Could not open %s" % arg)
    dest_f = (open(os.path.splitext(arg)[0] + "-parsed.xml", "w+") or
              die("Could not open destination file"))

    # The first line of the conditional xml has the tag containing
    # the kernel min LTS version.
    line = source_f.readline()
    exp_re = re.compile(r"^<kernel minlts=\"(\w+).(\w+).(\w+)\"\s+/>")
    exp_match = re.match(exp_re, line)
    if not exp_match:
        print("Malformatted kernel conditional config file.\n")
        exit(-1)
    major = exp_match.group(1)
    minor = exp_match.group(2)
    tiny = exp_match.group(3)

    line = source_f.readline()
    while line:
        line = line.replace("<value type=\"bool\">",
                "<value type=\"tristate\">")
        line = line.replace("<group>",
                "<kernel version=\"" + str(major) + "." + str(minor) +
                "." + str(tiny) + "\">")
        line = line.replace("</group>", "</kernel>")
        dest_f.write(line)
        line = source_f.readline()

    source_f.close()
    dest_f.close()

if len(sys.argv) == 1:
    print("Not enough arguments to kconfig_xml_fixup.py.")
    exit(-1)

for arg in sys.argv[1:]:
    fixup(arg)

exit(0)
