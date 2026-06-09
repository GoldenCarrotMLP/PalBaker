#include "AnimScriptingLibrary.h"
#include "Animation/AnimBlueprint.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_LocalToComponentSpace.h"
#include "AnimGraphNode_ComponentToLocalSpace.h"
#include "AnimGraphNode_ModifyBone.h"
#include "AnimGraphNode_SpringBone.h"
#include "AnimGraphNode_LinkedInputPose.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

bool UAnimScriptingLibrary::ApplyPalBakerRigging(UAnimBlueprint* AnimBP, const FString& JsonPath)
{
    if (!AnimBP) return false;

    // 1. Load JSON Metadata
    FString JsonStr;
    if (!FFileHelper::LoadFileToString(JsonStr, *JsonPath)) return false;

    TSharedPtr<FJsonObject> JsonObj;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonStr);
    if (!FJsonSerializer::Deserialize(Reader, JsonObj)) return false;

    // 2. Locate the AnimGraph
    UEdGraph* AnimGraph = nullptr;
    for (UEdGraph* Graph : AnimBP->FunctionGraphs) {
        if (Graph->GetFName() == TEXT("AnimGraph")) {
            AnimGraph = Graph;
            break;
        }
    }
    if (!AnimGraph) return false;

    // 3. Locate the Root Node and its Input Pin
    UAnimGraphNode_Root* RootNode = nullptr;
    for (UEdGraphNode* Node : AnimGraph->Nodes) {
        RootNode = Cast<UAnimGraphNode_Root>(Node);
        if (RootNode) break;
    }
    if (!RootNode) return false;

    UEdGraphPin* RootInputPin = RootNode->FindPin(TEXT("Result"));
    if (!RootInputPin) return false;

    UEdGraphPin* OriginalOutputPin = nullptr;
    int32 NodeX = RootNode->NodePosX - 400;
    int32 NodeY = RootNode->NodePosY;

    // If an existing blueprint, intercept the existing feed. 
    // If empty (newly generated), spawn an Input Pose node to drive the physics chain.
    if (RootInputPin->LinkedTo.Num() > 0) {
        OriginalOutputPin = RootInputPin->LinkedTo[0];
        RootInputPin->BreakAllPinLinks();
    } else {
        UAnimGraphNode_LinkedInputPose* InputNode = NewObject<UAnimGraphNode_LinkedInputPose>(AnimGraph);
        AnimGraph->AddNode(InputNode);
        InputNode->CreateNewGuid(); // FIX: Assign unique NodeGuid programmatically
        InputNode->AllocateDefaultPins();
        InputNode->Node.Name = FName(TEXT("InPose"));
        InputNode->NodePosX = NodeX - 400;
        InputNode->NodePosY = NodeY;
        
        OriginalOutputPin = InputNode->FindPin(TEXT("Pose"));
        if (!OriginalOutputPin) return false;
    }

    // --- Create Local to Component Space ---
    UAnimGraphNode_LocalToComponentSpace* L2C = NewObject<UAnimGraphNode_LocalToComponentSpace>(AnimGraph);
    AnimGraph->AddNode(L2C);
    L2C->CreateNewGuid(); // FIX: Assign unique NodeGuid programmatically
    L2C->AllocateDefaultPins();
    L2C->NodePosX = NodeX;
    L2C->NodePosY = NodeY;
    NodeX += 300;
    
    L2C->FindPin(TEXT("LocalPose"))->MakeLinkTo(OriginalOutputPin);
    UEdGraphPin* CurrentOutputPin = L2C->FindPin(TEXT("ComponentPose"));

    // --- Inject Offset Bones (ModifyBone) ---
    const TArray<TSharedPtr<FJsonValue>>* OffsetBones;
    if (JsonObj->TryGetArrayField(TEXT("offset_bones"), OffsetBones))
    {
        for (const auto& Val : *OffsetBones)
        {
            TSharedPtr<FJsonObject> BoneObj = Val->AsObject();
            
            UAnimGraphNode_ModifyBone* ModBone = NewObject<UAnimGraphNode_ModifyBone>(AnimGraph);
            AnimGraph->AddNode(ModBone);
            ModBone->CreateNewGuid(); // FIX: Assign unique NodeGuid programmatically
            ModBone->AllocateDefaultPins();
            ModBone->NodePosX = NodeX;
            ModBone->NodePosY = NodeY;
            NodeX += 300;

            ModBone->Node.BoneToModify.BoneName = FName(*BoneObj->GetStringField(TEXT("bone_name")));
            
            const TArray<TSharedPtr<FJsonValue>>* TransArr;
            if (BoneObj->TryGetArrayField(TEXT("translation"), TransArr)) {
                FVector TVal((*TransArr)[0]->AsNumber(), (*TransArr)[1]->AsNumber(), (*TransArr)[2]->AsNumber());
                ModBone->Node.Translation = TVal;
                if (UEdGraphPin* Pin = ModBone->FindPin(TEXT("Translation"))) {
                    Pin->DefaultValue = FString::Printf(TEXT("%f,%f,%f"), TVal.X, TVal.Y, TVal.Z);
                }
            }
            
            const TArray<TSharedPtr<FJsonValue>>* RotArr;
            if (BoneObj->TryGetArrayField(TEXT("rotation"), RotArr)) {
                FRotator RVal((*RotArr)[1]->AsNumber(), (*RotArr)[2]->AsNumber(), (*RotArr)[0]->AsNumber());
                ModBone->Node.Rotation = RVal;
                if (UEdGraphPin* Pin = ModBone->FindPin(TEXT("Rotation"))) {
                    Pin->DefaultValue = FString::Printf(TEXT("%f,%f,%f"), RVal.Pitch, RVal.Yaw, RVal.Roll);
                }
            }

            const TArray<TSharedPtr<FJsonValue>>* ScaleArr;
            if (BoneObj->TryGetArrayField(TEXT("scale"), ScaleArr)) {
                FVector SVal((*ScaleArr)[0]->AsNumber(), (*ScaleArr)[1]->AsNumber(), (*ScaleArr)[2]->AsNumber());
                ModBone->Node.Scale = SVal;
                if (UEdGraphPin* Pin = ModBone->FindPin(TEXT("Scale"))) {
                    Pin->DefaultValue = FString::Printf(TEXT("%f,%f,%f"), SVal.X, SVal.Y, SVal.Z);
                }
            }

            ModBone->Node.TranslationMode = EBoneModificationMode::BMM_Additive;
            ModBone->Node.RotationMode = EBoneModificationMode::BMM_Additive;
            ModBone->Node.ScaleMode = EBoneModificationMode::BMM_Replace;
            
            ModBone->Node.TranslationSpace = EBoneControlSpace::BCS_ParentBoneSpace;
            ModBone->Node.RotationSpace = EBoneControlSpace::BCS_ParentBoneSpace;
            ModBone->Node.ScaleSpace = EBoneControlSpace::BCS_BoneSpace;

            ModBone->FindPin(TEXT("ComponentPose"))->MakeLinkTo(CurrentOutputPin);
            CurrentOutputPin = ModBone->FindPin(TEXT("Pose"));
        }
    }

    // --- Inject Jiggle Bones (SpringBone) ---
    const TArray<TSharedPtr<FJsonValue>>* JiggleBones;
    if (JsonObj->TryGetArrayField(TEXT("jiggle_bones"), JiggleBones))
    {
        for (const auto& Val : *JiggleBones)
        {
            TSharedPtr<FJsonObject> BoneObj = Val->AsObject();
            
            UAnimGraphNode_SpringBone* SpringBone = NewObject<UAnimGraphNode_SpringBone>(AnimGraph);
            AnimGraph->AddNode(SpringBone);
            SpringBone->CreateNewGuid(); // FIX: Assign unique NodeGuid programmatically
            SpringBone->AllocateDefaultPins();
            SpringBone->NodePosX = NodeX;
            SpringBone->NodePosY = NodeY;
            NodeX += 300;

            SpringBone->Node.SpringBone.BoneName = FName(*BoneObj->GetStringField(TEXT("bone_name")));
            SpringBone->Node.SpringStiffness = BoneObj->GetNumberField(TEXT("spring_stiffness"));
            SpringBone->Node.SpringDamping = BoneObj->GetNumberField(TEXT("spring_damping"));
            SpringBone->Node.MaxDisplacement = BoneObj->GetNumberField(TEXT("max_displacement"));
            SpringBone->Node.ErrorResetThresh = BoneObj->GetNumberField(TEXT("error_reset_thresh"));
            SpringBone->Node.bLimitDisplacement = BoneObj->GetBoolField(TEXT("limit_displacement"));
            
            SpringBone->Node.bTranslateX = BoneObj->GetBoolField(TEXT("translate_x"));
            SpringBone->Node.bTranslateY = BoneObj->GetBoolField(TEXT("translate_y"));
            SpringBone->Node.bTranslateZ = BoneObj->GetBoolField(TEXT("translate_z"));
            SpringBone->Node.bRotateX = BoneObj->GetBoolField(TEXT("rotate_x"));
            SpringBone->Node.bRotateY = BoneObj->GetBoolField(TEXT("rotate_y"));
            SpringBone->Node.bRotateZ = BoneObj->GetBoolField(TEXT("rotate_z"));

            // Parse and apply the Alpha field to both the property and the exposed Pin
            if (BoneObj->HasField(TEXT("alpha"))) {
                float AlphaVal = BoneObj->GetNumberField(TEXT("alpha"));
                SpringBone->Node.Alpha = AlphaVal;
                
                UEdGraphPin* AlphaPin = SpringBone->FindPin(TEXT("Alpha"));
                if (AlphaPin) {
                    AlphaPin->DefaultValue = FString::Printf(TEXT("%f"), AlphaVal);
                }
            }

            SpringBone->FindPin(TEXT("ComponentPose"))->MakeLinkTo(CurrentOutputPin);
            CurrentOutputPin = SpringBone->FindPin(TEXT("Pose"));
        }
    }


    // --- Create Component to Local Space ---
    UAnimGraphNode_ComponentToLocalSpace* C2L = NewObject<UAnimGraphNode_ComponentToLocalSpace>(AnimGraph);
    AnimGraph->AddNode(C2L);
    C2L->CreateNewGuid(); // FIX: Assign unique NodeGuid programmatically
    C2L->AllocateDefaultPins();
    C2L->NodePosX = NodeX;
    C2L->NodePosY = NodeY;

    C2L->FindPin(TEXT("ComponentPose"))->MakeLinkTo(CurrentOutputPin);
    C2L->FindPin(TEXT("Pose"))->MakeLinkTo(RootInputPin);

    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(AnimBP);
    FKismetEditorUtilities::CompileBlueprint(AnimBP);

    return true;
}