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
	"strings"

	"github.com/google/blueprint"

	"android/soong/android"
)

var (
	pctx = android.NewPackageContext("android/kernel")

	kconfigXmlFixupRule = pctx.AndroidStaticRule("kconfig_xml_fixup", blueprint.RuleParams{
		Command:     `${kconfigXmlFixupCmd} --input ${in} --output-version ${outputVersion} --output-matrix ${out}`,
		Description: "kconfig_xml_fixup ${in}",
	}, "outputVersion")

	assembleVintfRule = pctx.AndroidStaticRule("assemble_vintf", blueprint.RuleParams{
		Command:     `${assembleVintfCmd} ${flags} -i ${in} -o ${out}`,
		Description: "assemble_vintf -i ${in}",
	}, "flags")
)

type KernelConfigProperties struct {
	Srcs []string
	Meta string
}

type KernelConfigRule struct {
	android.ModuleBase
	properties KernelConfigProperties

	outputPath android.WritablePath
}

func init() {
	pctx.HostBinToolVariable("assembleVintfCmd", "assemble_vintf")
	pctx.HostBinToolVariable("kconfigXmlFixupCmd", "kconfig_xml_fixup")
	android.RegisterModuleType("kernel_config", kernelConfigFactory)
}

func kernelConfigFactory() android.Module {
	g := &KernelConfigRule{}
	g.AddProperties(&g.properties)
	android.InitAndroidModule(g)
	return g
}

func (g *KernelConfigRule) OutputPath() android.Path {
	return g.outputPath
}

func (g *KernelConfigRule) DepsMutator(ctx android.BottomUpMutatorContext) {
	android.ExtractSourcesDeps(ctx, g.properties.Srcs)
	android.ExtractSourcesDeps(ctx, []string{g.properties.Meta})
}

func (g *KernelConfigRule) GenerateAndroidBuildActions(ctx android.ModuleContext) {
	g.outputPath = android.PathForModuleOut(ctx, g.Name()+".xml")
	genVersion := android.PathForModuleGen(ctx, g.Name()+".version.txt")
	inputMeta := android.PathForModuleSrc(ctx, g.properties.Meta)
	genConditionals := android.PathForModuleGen(ctx, g.properties.Meta)

	if len(g.properties.Meta) == 0 {
		ctx.PropertyErrorf("kernel_config", "Missing meta field")
	}

	ctx.Build(pctx, android.BuildParams{
		Rule:           kconfigXmlFixupRule,
		Description:    "Fixup kernel config meta",
		Input:          inputMeta,
		Output:         genConditionals,
		ImplicitOutput: genVersion,
		Args: map[string]string{
			"outputVersion": genVersion.String(),
		},
	})

	var kernelArg string
	var implicitInputs android.Paths
	implicitInputs = make([]android.Path, len(g.properties.Srcs)+1)
	implicitInputs[len(g.properties.Srcs)] = genVersion
	if len(g.properties.Srcs) > 0 {
		inputConfigs := make([]string, len(g.properties.Srcs))
		for i, src := range g.properties.Srcs {
			implicitInputs[i] = android.PathForModuleSrc(ctx, src)
			inputConfigs[i] = implicitInputs[i].String()
		}
		kernelArg = "--kernel=$$(cat " + genVersion.String() + "):" +
			strings.Join(inputConfigs, ":")
	}

	ctx.Build(pctx, android.BuildParams{
		Rule:        assembleVintfRule,
		Description: "Framework Compatibility Matrix kernel fragment",
		Input:       genConditionals,
		Implicits:   implicitInputs,
		Output:      g.outputPath,
		Args: map[string]string{
			"flags": kernelArg,
		},
	})

}
