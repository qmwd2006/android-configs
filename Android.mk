LOCAL_PATH := $(call my-dir)

kconfig_xml_fixup := $(LOCAL_PATH)/tools/kconfig_xml_fixup.py

kernel_cond_xml_src := \
  $(call all-named-files-under,android-base-conditional.xml)

kernel_cond_xml := $(addprefix $(call intermediates-dir-for,ETC,kernel_cond)/,$(subst .xml,-parsed.xml,$(kernel_cond_xml_src)))
kernel_cond_xml_in := $(addprefix $(LOCAL_PATH)/,$(kernel_cond_xml_src))

$(kernel_cond_xml): $(kernel_cond_xml_in) $(kconfig_xml_fixup)
	$(kconfig_xml_fixup) $(call intermediates-dir-for,ETC,kernel_cond) "kernel/configs" $(kernel_cond_xml_src)
