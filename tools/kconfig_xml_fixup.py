#!/usr/bin/env python

# The format of the kernel configs in the framework compatibility matrix
# has a couple properties that would make it confusing or cumbersome to
# maintain by hand:
#
#  - Conditions apply to all configs within the same <kernel> section.
#    The <kernel> tag also specifies the LTS version. Since the entire
#    file in the kernel/configs repo is for a single kernel version,
#    the section is renamed as a "group", and the LTS version is
#    specified once at the top of the file with a tag of the form
#    <kernel minlts="x.y.z" />.
#  - The compatibility matrix understands all kernel config options as
#    tristate values. In reality however some kernel config options are
#    boolean. This script simply converts booleans to tristates so we
#    can avoid describing boolean values as tristates in hand-maintained
#    files.
#
# Usage:
# kconfig_xml_fixup.py <out dir> <location of configs repo> <input xml files>

from __future__ import print_function
import os
import re
import sys

def fixup(outdir, arg):
    source_f = open(config_repo +"/" + arg) or die ("Could not open %s" % arg)
    dest_f = (open(outdir + "/" + os.path.splitext(arg)[0] + "-parsed.xml", "w+") or
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

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Not enough arguments to kconfig_xml_fixup.py.")
        exit(-1)

    config_repo = sys.argv[2]

    for arg in sys.argv[3:]:
        fixup(sys.argv[1], arg)

    exit(0)
