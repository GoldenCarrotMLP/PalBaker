import actionRulesData from "./action-rules.json"

export interface NotifyRule {
  Key: string
  Status: "REQUIRED" | "COMMON" | "OPTIONAL"
  DetailType: string
  IsStateNotify: boolean
  SocketAttachedRequired: boolean
  Templates?: string[]
}

export interface ActionRule {
  Action: string
  IsLooping: boolean
  ExpectedSectionFlow: string
  MultiSegmentExpected: boolean
  NotifyRules: NotifyRule[]
}

export const ACTION_RULES: Record<string, ActionRule> = actionRulesData as Record<string, ActionRule>

export function findActionRule(actionName: string): ActionRule | null {
  if (!actionName) return null
  const clean = actionName.trim()

  // 1. Direct match
  if (ACTION_RULES[clean]) return ACTION_RULES[clean]

  // 2. Strip AM_ / AS_ / PalName prefixes
  const stripped = clean.replace(/^(?:AM|AS)_[a-zA-Z0-9]+?_/, "")
  if (ACTION_RULES[stripped]) return ACTION_RULES[stripped]

  // 3. Case-insensitive lookup
  const cleanLower = clean.toLowerCase()
  const strippedLower = stripped.toLowerCase()
  for (const [k, rule] of Object.entries(ACTION_RULES)) {
    const kLower = k.toLowerCase()
    if (kLower === cleanLower || kLower === strippedLower) {
      return rule
    }
  }

  return null
}

export interface MontageValidationResult {
  isValid: boolean
  actionRule: ActionRule | null
  missingRequired: NotifyRule[]
  missingCommon: NotifyRule[]
}

export function validateMontageNotifies(
  actionName: string,
  notifies: Array<{ Name: string; EventName?: string }>
): MontageValidationResult {
  const rule = findActionRule(actionName)
  if (!rule) {
    return { isValid: true, actionRule: null, missingRequired: [], missingCommon: [] }
  }

  const matchesRule = (notifyRule: NotifyRule): boolean => {
    const targetKey = notifyRule.Key
    const targetParts = targetKey.split(":")
    const mainType = targetParts[0]
    const subEvent = targetParts[1] // e.g. "Starttossin" in "PlayMontageNotify:Starttossin"

    return notifies.some((n) => {
      const nName = n.Name || ""
      const nEvent = n.EventName || ""

      // Exact match
      if (nName === targetKey || nName.toLowerCase() === targetKey.toLowerCase()) return true

      // If rule is "Type:Event" (e.g. PlayMontageNotify:Starttossin)
      if (subEvent) {
        if (nName === mainType && nEvent.toLowerCase() === subEvent.toLowerCase()) return true
        if (nName.toLowerCase() === subEvent.toLowerCase()) return true
        if (nEvent.toLowerCase() === subEvent.toLowerCase()) return true
      }

      // Main type match without sub-event
      if (nName === mainType && !subEvent) return true

      // Common type aliases & partials
      if (mainType === "PalEffect" && (nName === "PalEffect" || nName.includes("Effect"))) return true
      if (mainType === "PalAttackCollision" && (nName === "PalAttackCollision" || nName.includes("Collision"))) return true
      if (mainType === "BP_FootStep_C" && (nName.includes("FootStep") || nName === "BP_FootStep_C")) return true
      if (mainType.includes("AkEvent") && (nName.includes("AkEvent") || nName.includes("Sound"))) return true
      if (mainType.includes("Niagara") && (nName.includes("Niagara") || nName.includes("Effect"))) return true

      return false
    })
  }

  const missingRequired = rule.NotifyRules.filter((r) => r.Status === "REQUIRED" && !matchesRule(r))
  const missingCommon = rule.NotifyRules.filter((r) => r.Status === "COMMON" && !matchesRule(r))

  return {
    isValid: missingRequired.length === 0,
    actionRule: rule,
    missingRequired,
    missingCommon,
  }
}