---
description: Check platform governance before implementing
---

# Governance Check

- ❌ `import anthropic`/`openai` → ✅ `iil-aifw`
- ❌ Hardcoded secrets → ✅ `decouple.config()`
- ❌ Inline prompts → ✅ `iil-promptfw`
- ❌ Raw SQL → ✅ Django ORM
