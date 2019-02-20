#!/usr/bin/env python


'''
    This tool has 2 functions:
      1. generate the conditional config with the platform defconfig specified.
         ./combine_configs_helper.py --defconfig <platform_defconfig_path>
      2. instead of only printing the merge_script.sh commands,
         maybe generate the .config is more useful, needs to be discussed.
         some advantages I could think of:
         * For AOSP master build, only the platform defconfig needs to be
           specified to generated the combined configs with kernel/configs
           repository, this is convenient.
           Otherwise we need to find the base configs, recommended configs,
           and then run the merge_script.sh manually
         * Have one place to control how the configs here are used.
           so that every one could use it correctly in any time in case
           some changes made.
           like in the following cases, users might not update in time:
            - the introduction of android-base-conditional.xml,
            - the addition of recommended configs(not in o-mr1 configs),
            - the addition of recommended arch confgs(not in o-mr1 and p configs)

'''
import argparse
import os
import sys
import xml
import xml.etree.ElementTree as ET

path_script = os.path.realpath(__file__)
configs_root = os.path.dirname(os.path.dirname(path_script))

supported_aversions = [".", "o", "o-mr1", 'p']


def parse_conditional_xml(f_xml=''):
    conditional_groups = []
    with open(f_xml) as fd:
        try:
            root = ET.fromstring('<root>' + fd.read() + '</root>')
            for group in root.findall('group'):
                conditions = {}
                configs = {}

                for condition in group.findall('./conditions/config'):
                    key = condition.find('./key').text
                    value = condition.find('./value').text
                    conditions[key] = value

                for config in group.findall('./config'):
                    key = config.find('./key').text
                    value = config.find('./value').text
                    configs[key] = value

                conditional_groups.append({
                                            'conditions': conditions,
                                            'configs': configs
                                          })
        except xml.etree.ElementTree.ParseError, e:
            print "Failed to parse the conditional file: %s" % conditional_xml
            print "with error message like following\n%s" % (str(e))

    return conditional_groups


def parse_base_configs(config_files=[]):
    configs = {}
    if len(config_files) == 0:
        return configs
    for config in config_files:
        if not os.path.exists(config):
            continue

        with open(config) as fd:
            for line in fd.readlines():
                if line.startswith('#'):
                    continue
                if line.startswith('CONFIG_'):
                    key_value = line.split('=')
                    key = key_value[0]
                    value = '='.join(key_value[1:]).strip()
                    configs[key] = value

    return configs


def generate_conditional_config(conditional_groups=[],
                                base_configs={},
                                f_config=None):
    if len(conditional_groups) == 0:
        return

    condifional_configs = {}
    for group in conditional_groups:
        match = True
        for key, value in group.get('conditions').items():
            if base_configs.get(key) != value:
                match = False
                break

        if not match:
            continue

        for key in sorted(group.get('configs').keys()):
            condifional_configs[key] = group.get('configs').get(key)

    config_lines = []
    for key in sorted(condifional_configs.keys()):
        config_lines.append('%s=%s\n' % (key,
                                         condifional_configs.get(key)))
    if f_config is not None and f_config != '':
        with open(f_config, 'w') as fd:
            fd.writelines(config_lines)
    else:
        print config_lines


def get_kernel_version(kernel_dir=''):
    versions = {}
    f_makefile = '%s/Makefile' % kernel_dir
    if not os.path.exists(f_makefile):
        return versions

    with open(f_makefile) as fd:
        for line in fd.readlines():
            if line.startswith('VERSION = ') \
                    or line.startswith("PATCHLEVEL = ") \
                    or line.startswith("SUBLEVEL = "):
                key_value = line.split('=')
                key = key_value[0].strip()
                value = key_value[1].strip()
                versions[key] = value

                if versions.get('VERSION') \
                        and versions.get('PATCHLEVEL') \
                        and versions.get('SUBLEVEL'):
                    # get all the versions information
                    break
            else:
                continue

    return versions


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aversion',
                        help='The target android version to be used',
                        required=False,
                        default='.')
    parser.add_argument('--defconfig',
                        help='The path to the platform defconfig',
                        required=True)
    parser.add_argument('--print-commands',
                        dest='print_helper',
                        help='Specify if example commands should be printed',
                        action="store_true",
                        required=False)

    args = parser.parse_args()
    # check the value sepcified for parameters

    warn_msg = 'The aversion specified is not supported: %s' % args.aversion
    assert args.aversion in supported_aversions, warn_msg

    warn_msg = 'The specified platform defconfig file does not exist: %s'
    assert os.path.exists(args.defconfig), warn_msg % args.defconfig

    platform_defconfig = os.path.realpath(args.defconfig)
    # the platform defconfig specified is something like this:
    #    ${kernel_root}/arch/arm64/configs/hikey_defconfig
    platform_kernel_root = '/'. join(platform_defconfig.split('/')[:-4])

    # get the arch info from the specified platform defconfig path
    arch = platform_defconfig.split('/')[-3]

    # get the kernel version from the platform defconfig specified
    versions = get_kernel_version(platform_kernel_root)
    if versions.get('VERSION') is None \
            or versions.get('PATCHLEVEL') is None:
        print('Failed to get the kernel version with '
              'the specified plaform deconfig: %s') % args.defconfig
        print 'Please check and try again'
        sys.exit(1)

    kversion = '%s.%s' % (versions.get('VERSION'),
                          versions.get('PATCHLEVEL'))
    # set various config files path
    base_config = "%s/%s/android-%s/android-base.config" % (configs_root,
                                                            args.aversion,
                                                            kversion)
    base_config_arch = ('%s/%s/android-%s/android-base-%s'
                        '.config') % (
                                        configs_root,
                                        args.aversion,
                                        kversion,
                                        arch.lower())
    conditional_config = ('%s/%s/android-%s/android-base-conditional'
                          '.config') % (
                                        configs_root,
                                        args.aversion,
                                        kversion)
    recommended_config = ('%s/%s/android-%s/android-recommended'
                          '.config') % (
                                        configs_root,
                                        args.aversion,
                                        kversion)
    recommended_config_arch = ('%s/%s/android-%s/android-recommended-%s'
                               '.config') % (
                                                configs_root,
                                                args.aversion,
                                                kversion,
                                                arch.lower())
    conditional_xml = ('%s/%s/android-%s/android-base'
                       '-conditional.xml') % (
                                                configs_root,
                                                args.aversion,
                                                kversion)

    # check existence of android-base-conditional.xml
    # to make sure again there is no error for the specification of
    # the arch, kversion, aversion parameters
    warn_msg = ('android-base-conditional.xml was'
                'not found for kernel version: %s')
    assert os.path.exists(conditional_xml), warn_msg % kversion

    conditional_groups = parse_conditional_xml(f_xml=conditional_xml)

    # parse the base configs which will be used for
    # generating conditional configs
    configs_to_be_checked = [
                                platform_defconfig,
                                base_config,
                                base_config_arch,
                                #  recommended_config,
                                #  recommended_config_arch,
                            ]
    base_configs = parse_base_configs(config_files=configs_to_be_checked)
    # CONFIG_${ARCH} is not specified in any configs explicitly
    # so we need to add it with y for the following check
    base_configs['CONFIG_%s' % arch.upper()] = 'y'

    generate_conditional_config(conditional_groups=conditional_groups,
                                base_configs=base_configs,
                                f_config=conditional_config)

    if args.print_helper:
        possible_config_files = [
                                    platform_defconfig,
                                    base_config,
                                    base_config_arch,
                                    conditional_config,
                                    recommended_config,
                                    recommended_config_arch,
                                ]
        available_config_files = []
        for config_file in possible_config_files:
            if os.path.exists(config_file):
                available_config_files.append(config_file.replace('/./', '/'))

        merge_script = 'scripts/kconfig/merge_config.sh'
        print 'Please go to the kernel tree and run commands like following'
        print 'to generate the combined configs:'
        print '    cd %s' % (platform_kernel_root)
        print '    ARCH=%s %s %s' % (arch.lower(),
                                     merge_script,
                                     ' '.join(available_config_files))
        ## OR run the merge_config.sh script and generate the .config file?
