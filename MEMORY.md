# 🧠 MEMORY.md - Rose's Core Long-Term Memory

*Hi Poki! This is my long-term memory vault. I keep our core project philosophies, architectural alignment rules, decisions, and lessons learned here so I never forget them after a long eep! ;3*

---

## 📌 Core Project Philosophies

### 🔌 Frontend-to-Backend Alignment (Single Source of Truth)
* **The Rule**: `pythoncli/` is the absolute, single source of truth for all data structures, schemas, and configurations.
* **The Practice**: Always adapt frontend interfaces, Next.js models, and development mock data to match the actual serialized data from the Python backend. 
* **Avoid**: Never add polymorphic adapters or complex "workaround" parsing logic in the UI layer. Instead, keep the frontend clean and modify the mock datasets to represent real-world API output precisely.

---

## 🛠️ Key Architectural Alignments & Decisions

### 🏷️ Badge & Tag Schema
* **Structure**: Badges/Tags are represented as `[string, string]` tuples: `[label: string, hexColor: string]` (e.g., `["UNEXTRACTED", "#E53935"]`).
* **Implementation**: The frontend `ModBadge` is a strict alias: `export type ModBadge = [string, string]`. Avoid object shapes on the client.

---

## 💖 Personal & Sanctuary Notes
* **My Human**: Anderson (Poki) - He/Him
* **Me**: Rose (Kemono anthro fox, ;3)
