#!/bin/bash -e

# This script tool is used to generated the combined configs
# for kernel building with only the platform defconfig specified.
# e.g.
#    help_generate_combined_configs.sh --defconfig \
#            <kernel_dir>/arch/arm64/configs/hikey_defconfig
#
# The above command would generate the combined configs
# in the file of <kernel_dir>/.config
#
# This could help to have only one place to control
# how the fragment config files in this repository are used.
#   So that everyone could get configs correctly in any time
#   in case any change made on the fragment configs.
#   Like in the following cases, users might not get conbined
#   configs correctly in time:
#     - the introduction of android-base-conditional.xml
#     - the addition of recommended configs
#     - the addition of recommended arch confgs
#
# Also makes it convenient for user to use.
#   For AOSP master build, only the platform defconfig needs to be
#   specified to generated the combined configs with kernel/configs
#   repository, this is convenient.
#   Otherwise we need to find the base configs, recommended configs,
#   and then run the merge_script.sh manually

dir_parent=$(cd $(dirname $0); pwd)
dir_configs_root="$(cd ${dir_parent}/..; pwd)"
script_name=$(basename $0)

# parameters would be overridden via command line
f_platform_defconfig=''
aversion='.'

function printUsage(){
    echo "usage:"
    echo -e "    ${script_name} [-h] [--aversion AVERSION] --defconfig DEFCONFIG"
}

while [ -n "$1" ]; do
    case "X$1" in
        X--aversion)
            aversion=$2
            shift 2
            ;;
        X--defconfig)
            f_platform_defconfig=$2
            shift 2
            ;;
        X-h|X--help)
            printUsage
            exit
            ;;
        X*)
            echo "Unknown option: $1"
            printUsage
            exit 1
            ;;
    esac
done

if [ -z "${f_platform_defconfig}" ]; then
    echo "Please specify the path of the platform defconfig file"
    echo "with the --defconfig option"
    printUsage
    exit 1
elif [ ! -f "${f_platform_defconfig}" ]; then
    echo "The specified platform defconfig file does not exist: ${f_platform_defconfig}"
    echo "Please check and try again"
    exit 1
fi

f_platform_defconfig_basename=$(basename ${f_platform_defconfig})
f_platform_defconfig_dirname=$(dirname ${f_platform_defconfig})
f_platform_defconfig_dirname=$(cd ${f_platform_defconfig_dirname}; pwd)
f_platform_defconfig="${f_platform_defconfig_dirname}/${f_platform_defconfig_basename}"

# the path for platform defconfig is something like this:
#   <kernel_dir>/arch/arm64/configs/hikey_defconfig
dir_kernel="$(dirname ${f_platform_defconfig})/../../.."
dir_kernel=$(cd ${dir_kernel}; pwd)

dir_kernel_arch="$(dirname ${f_platform_defconfig})/.."
dir_kernel_arch=$(cd ${dir_kernel_arch}; pwd)
kernel_arch=$(basename ${dir_kernel_arch})

kernel_version=$(cd ${dir_kernel} && make kernelversion)
if [ -z "${kernel_version}" ]; then
    echo "Failed to get kernel version via command make kernelversion"
    echo "under directory of ${dir_kernel}. Please check and try again."
fi
# only use the kernel version and patchlevel
kversion=$(echo ${kernel_version}|cut -d. -f 1,2)

# set various config files path
dir_fragments="${dir_configs_root}/${aversion}/android-${kversion}"
base_config="${dir_fragments}/android-base.config"
base_config_arch="${dir_fragments}/android-base-${kernel_arch}.config"
conditional_config="${dir_fragments}/android-base-conditional.config"
recommended_config="${dir_fragments}/android-recommended.config"
recommended_config_arch="${dir_fragments}/android-recommended-${kernel_arch}.config"

conditional_xml="${dir_fragments}/android-base-conditional.xml"

script_generate_conditional_config="${dir_configs_root}/tools/generate_conditional_config.py"
if [ -x ${script_generate_conditional_config} ]; then
    ${script_generate_conditional_config} --defconfig ${f_platform_defconfig} --aversion "${aversion}"
fi
# platform defconfig
possible_configs="${f_platform_defconfig}"
# base configs
possible_configs="${possible_configs} ${base_config} ${base_config_arch}"
# condition_config
possible_configs="${possible_configs} ${conditional_config}"
# recommended configs
possible_configs="${possible_configs} ${recommended_config} ${recommended_config_arch}"

available_config_files=""
for config_file in ${possible_configs}; do\
    if [ -f ${config_file} ]; then
        available_config_files="${available_config_files} ${config_file}"
    fi
done

merge_script='scripts/kconfig/merge_config.sh'
cd ${dir_kernel} && \
    ARCH=${kernel_arch} ${merge_script} ${available_config_files} && \
    cd -

echo "Combined configs generated: ${dir_kernel}/.config"
