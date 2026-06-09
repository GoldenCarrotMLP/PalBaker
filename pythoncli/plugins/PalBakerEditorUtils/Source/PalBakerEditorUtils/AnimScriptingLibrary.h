#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "AnimScriptingLibrary.generated.h"

class UAnimBlueprint;

UCLASS()
class PALBAKEREDITORUTILS_API UAnimScriptingLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category = "PalBaker")
    static bool ApplyPalBakerRigging(UAnimBlueprint* AnimBP, const FString& JsonPath);
};
