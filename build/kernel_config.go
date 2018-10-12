// Copyright (C) 2018 The Android Open Source Project
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package kernel

import (
	"fmt"
	"io"
	"path/filepath"
	"strings"

	"github.com/google/blueprint"

	"android/soong/android"
)

var (
	pctx = android.NewPackageContext("android/kernel")
)

type KernelConfigProperties struct {
	Srcs []string
	Meta string
}

type KernelConfigRule struct {
	android.ModuleBase
	properties KernelConfigProperties

	srcDir            string
	genDir            string
	outputFile        string
	outputVersionFile string
	configs           []string

	srcVintfFragment string
	genVintfFragment string
}

func init() {
	android.RegisterModuleType("kernel_config", kernelConfigFactory)
}

func kernelConfigFactory() android.Module {
	g := &KernelConfigRule{}
	g.AddProperties(&g.properties)
	android.InitAndroidModule(g)
	return g
}

var _ android.AndroidMkDataProvider = (*KernelConfigRule)(nil)

func (g *KernelConfigRule) OutputCompatibilityMatrixFile() string {
	return g.outputFile
}

func (g *KernelConfigRule) DepsMutator(ctx android.BottomUpMutatorContext) {
	android.ExtractSourcesDeps(ctx, g.properties.Srcs)
	android.ExtractSourcesDeps(ctx, []string{g.properties.Meta})
	ctx.AddDependency(ctx.Module(), nil, "kconfig_xml_fixup")
	ctx.AddVariationDependencies([]blueprint.Variation{
		{Mutator: "arch", Variation: ctx.Config().BuildOsVariant},
	}, nil, "assemble_vintf")
}

func (g *KernelConfigRule) GenerateAndroidBuildActions(ctx android.ModuleContext) {
	g.srcDir = android.PathForModuleSrc(ctx).String()
	g.genDir = android.PathForModuleGen(ctx).String()
	g.outputFile = android.PathForModuleGen(ctx, g.Name()+".xml").String()
	g.outputVersionFile = android.PathForModuleGen(ctx, g.Name()+".version.txt").String()

	if len(g.properties.Meta) == 0 {
		ctx.PropertyErrorf("kernel_config", "Missing meta field")
	}

	g.srcVintfFragment = android.PathForModuleSrc(ctx, g.properties.Meta).String()
	g.genVintfFragment = android.PathForModuleGen(ctx, g.properties.Meta).String()

	for _, src := range g.properties.Srcs {
		g.configs = append(g.configs, filepath.Join(g.srcDir, src))
	}

}

func gen(w io.Writer, out string, deps []string, args []string) {
	fmt.Fprintln(w, "GEN :=", out)
	fmt.Fprint(w, "$(GEN): ")
	fmt.Fprintln(w, strings.Join(deps, " "))
	fmt.Fprint(w, "\t")
	fmt.Fprintln(w, strings.Join(args, " "))
	fmt.Fprintln(w, "GEN :=")
}

func (g *KernelConfigRule) AndroidMk() android.AndroidMkData {
	return android.AndroidMkData{
		Custom: func(w io.Writer, name, prefix, moduleDir string, data android.AndroidMkData) {
			fmt.Fprintln(w)
			fmt.Fprintln(w, "include $(CLEAR_VARS)")
			fmt.Fprintln(w, "LOCAL_PATH :=", moduleDir)
			fmt.Fprintln(w, "LOCAL_MODULE :=", g.Name())
			fmt.Fprintln(w, "LOCAL_MODULE_CLASS := ETC")
			fmt.Fprintln(w, "LOCAL_MODULE_PATH :=", g.genDir)

			if len(g.configs) > 0 {
				gen(w, g.outputVersionFile,
					[]string{"$(HOST_OUT_EXECUTABLES)/kconfig_xml_fixup",
						g.srcVintfFragment},
					[]string{"$(HOST_OUT_EXECUTABLES)/kconfig_xml_fixup",
						"--input", g.srcVintfFragment, "--output-version", "$@"})
			}

			gen(w, g.genVintfFragment,
				[]string{"$(HOST_OUT_EXECUTABLES)/kconfig_xml_fixup",
					g.srcVintfFragment},
				[]string{"$(HOST_OUT_EXECUTABLES)/kconfig_xml_fixup",
					"--input", g.srcVintfFragment,
					"--output-matrix", "$@"})

			args := []string{
				"$(HOST_OUT_EXECUTABLES)/assemble_vintf",
				"-i ", g.genVintfFragment,
				"-o", "$@"}

			deps := []string{"$(HOST_OUT_EXECUTABLES)/assemble_vintf"}
			deps = append(deps, g.genVintfFragment)
			deps = append(deps, g.configs...)

			if len(g.configs) > 0 {
				deps = append(deps, g.outputVersionFile)
				args = append(args, "--kernel=$$(cat "+g.outputVersionFile+"):"+
					strings.Join(g.configs, ":"))
			}

			gen(w, g.outputFile, deps, args)

			fmt.Fprintln(w, "LOCAL_PREBUILT_MODULE_FILE :=", g.outputFile)
			fmt.Fprintln(w, "include $(BUILD_PREBUILT)")
		},
	}
}
