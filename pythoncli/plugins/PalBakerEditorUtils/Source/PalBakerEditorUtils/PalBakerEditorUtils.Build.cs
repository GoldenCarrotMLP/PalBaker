using UnrealBuildTool;

public class PalBakerEditorUtils : ModuleRules
{
    public PalBakerEditorUtils(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
        PrivateDependencyModuleNames.AddRange(new string[] { 
            "UnrealEd", "BlueprintGraph", "AnimGraph", "AnimGraphRuntime", "Json", "JsonUtilities" 
        });
    }
}
