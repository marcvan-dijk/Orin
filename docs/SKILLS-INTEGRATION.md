# Orin + Julius Skills Integration

**Status:** Ready to implement  
**Purpose:** Adopt 8 proven AI agent skills for efficient communication, code quality, and task management  
**Approach:** Submodule + selective skill activation per workflow

---

## Why This Matters

The Orin project involves:
- Complex AI-assisted authoring (human-AI collaboration)
- Code generation from intent (quality control needed)
- Multi-backend equivalence proofs (precision required)
- Long agent sessions (context decay risk)

**Julius Skills** directly address these:

| Orin Need | Julius Skill | Benefit |
|-----------|--------------|---------|
| Concise AI proposals | **Caveman** | 65-75% token reduction; preserve technical accuracy |
| High-quality generated code | **Interface Kit** + **Last 20%** | Accessible, performant, complete artifacts |
| Rigorous plan review | **Junior to Senior** | Staff-engineer-grade critique; surface assumptions |
| Long session health | **Context Canary** | Early warning when context degrades |
| Calibrated pressure testing | **Grill Me** | One-at-a-time questions matched to user knowledge |
| Clean proposal text | **Deslopify** | Remove AI-writing tells from semantic patch descriptions |
| Spec-driven loops | **Loop Factory** | Inbox → Active → Archive; hard review gates |
| Base efficiency | **Caveman base** | 70k-star token compression; foundational |

---

## Integration Architecture

### Step 1: Add as Git Submodule

```bash
# In marcvan-dijk/Orin root
git submodule add https://github.com/JuliusBrussee/skills.git vendor/skills
git submodule update --init --recursive

# Commit
git add .gitmodules vendor/skills
git commit -m "Add Julius Skills as submodule for AI efficiency"
```

### Step 2: Skill Activation Points

Create a skills manifest for Orin:

```yaml
# .orin/skills-config.yaml
skills:
  caveman:
    enabled: true
    intensity: "full"  # lite | full | ultra
    contexts:
      - "AI proposals"  # Deslopify + Caveman for proposal text
      - "diagnostic-messages"  # Keep errors terse but clear
    exit-command: "stop caveman"
  
  interface-kit:
    enabled: true
    contexts:
      - "generated-web-artifacts"  # Quality UI from TypeScript backend
      - "VS Code extension UX"
    reference-file: "docs/DESIGN.md"
  
  junior-to-senior:
    enabled: true
    contexts:
      - "backend-equivalence-review"  # Before accepting as proof
      - "semantic-model-critique"  # Before finalizing major decisions
    checklist:
      - "interfaces committed?"
      - "versions explicit?"
      - "failure modes documented?"
  
  deslopify:
    enabled: true
    contexts:
      - "semantic-patch descriptions"  # Remove "explores", "provides", etc.
      - "documentation passes"
    registers:
      - "technical" # Keep academic/formal
  
  context-canary:
    enabled: true
    contexts:
      - "long-session human-AI pairing"
      - "multi-turn semantic refinement"
    health-check-interval: "every-turn"
  
  grill-me:
    enabled: true
    contexts:
      - "user research sessions (M7)"  # Calibrated interview
      - "design decisions"
    pressure-levels: ["working", "expert"]
  
  loop-factory:
    enabled: true
    contexts:
      - "M1-M4 task management"
      - "CI/CD test suite"
    task-states: ["inbox", "active", "review", "archive"]
  
  last-20-percent:
    enabled: true
    contexts:
      - "end-to-end demo (M4)"  # Golden path walkthrough
      - "first-run experience"
      - "web artifact experience"
```

### Step 3: Skill Integration Points

#### 3.1 Caveman for Proposal Descriptions

**When:** AI generates semantic patch  
**How:** Apply Caveman full mode to proposal description  
**Example:**

```python
# implementations/python/proposals.py
from vendor.skills.scripts.caveman import compress_text

proposal = {
    "type": "add_capability",
    "original_description": "This proposal explores the possibility of adding a new persistent effect boundary to handle transaction rollback scenarios in account-store interactions.",
    "affected_objects": ["AccountStoreEffect", "request-reset workflow"]
}

# Apply Caveman
proposal["caveman_description"] = compress_text(
    proposal["original_description"],
    intensity="full"
)
# Output: "Add persistent effect boundary. Handles account-store rollback in reset workflow."
```

#### 3.2 Junior-to-Senior for Equivalence Proof

**When:** Both backends pass examples; before marking M4 exit gate  
**How:** Run generated TypeScript backend through senior review checklist  
**Checklist:**

```markdown
## Senior Review: TypeScript Backend

- [ ] **Interfaces committed:** Are all workflow I/O types explicit? Any hand-waving on error contracts?
  - Grep: `any` type usage, implicit `unknown`, missing error fields
  
- [ ] **Versions explicit:** Does generated code pin versions? Dependencies locked?
  - Check: package-lock.json, TypeScript version, adapter interface contracts
  
- [ ] **Failure modes documented:** Can the code fail? Where? What's the recovery?
  - For each effect (AccountStore lookup, Email send):
    - What if adapter unreachable?
    - What's the observable output to user?
    - Is it caught by test examples?
    
- [ ] **Edge cases covered:** Token expiry, concurrent requests, state races?
  - Refer: password-reset.cases.json — do all 5 examples pass?
  
- [ ] **Capability enforcement:** Can unauthorized workflow be accepted?
  - Check: generated code enforces `required_capabilities` before effects

- [ ] **Evidence linked:** Can we audit why this code was accepted?
  - Check: evidence records linked to this artifact build
```

**Tool:** Create `implementations/typescript/SENIOR-REVIEW.md` template; fill before M4 exit.

#### 3.3 Interface Kit for Generated Web Artifacts

**When:** Web profile (M5) generates forms, pages  
**How:** Apply Interface Kit standard to all generated HTML/CSS/React  
**Reference:** Create `docs/DESIGN.md`

```markdown
# Design Standard for Orin Web Artifacts

## Accessibility First
- Contrast: WCAG AA minimum (4.5:1 for text)
- Keyboard: Full keyboard navigation, focus visible
- Semantics: Proper form labels, ARIA where needed

## Performance Before Decoration
- No flash of unstyled content
- CSS transforms only (no layout shifts)
- Lazy-load external data after interactive shell

## Typography Matters
- Base: 16px (readable at arm's length)
- Line-height: 1.5+ (readable columns)
- Tabular numbers for token displays

## Complete Component States
- Hover (mouse)
- Focus (keyboard)
- Active (pressed)
- Disabled (permissions denied)
- Loading (awaiting effect)
- Error (effect failed)
- Empty (no data yet)

Example: Reset email form
```

#### 3.4 Deslopify for Documentation Passes

**When:** Writing semantic patch descriptions, evidence reports  
**How:** Scan for AI-writing tells; rewrite  
**Tells to scan:**

```javascript
// vendor/skills/skills/deslopify/tells.json
const tells = [
  "provides", "explores", "leverages", "harnesses",
  "enables", "empowers", "delightful",
  "not X but Y", "at its core",
  "rule of three", "false ranges" ("some...many"),
  "em-dash abuse"
]
```

**Integration:**

```python
# docs/generate_evidence_report.py
from vendor.skills.scripts.deslopify import scan_and_fix

proposal_text = """
This proposal provides a way to leverage the new persistent 
effect boundary, empowering robust transaction handling.
"""

result = scan_and_fix(proposal_text, register="technical")
# Rewritten: "Persistent effect boundary for transaction rollback."
# Tells found: ["provides", "leverage", "empowers"]
```

#### 3.5 Context Canary for Long Sessions

**When:** Multi-turn human-AI authoring (M6+)  
**How:** Inject canary signal every turn; detect degradation  
**Canary data:**

```python
# implementations/python/canary.py
from vendor.skills.scripts.context_canary import canary_signal

turn_data = {
    "user_name": "marcvan-dijk",
    "turn_number": 42,
    "model": "claude-3.5-sonnet",
    "context_tokens_used": 185000,
    "context_tokens_limit": 200000,
    "tokens_remaining": 15000,
}

signal = canary_signal(turn_data)
# Output: HEALTHY | DEGRADED | CRITICAL

if signal == "DEGRADED":
    print("⚠️ Context health declining. Recommend checkpoint + fresh session.")
```

#### 3.6 Loop Factory for Task Management

**When:** M1-M4 task execution  
**How:** Track tasks through inbox → active → archive; hard review gate  
**Task format (Markdown):**

```markdown
# Task: M1.3 — Capability & Effect Linking

**Status:** active  
**Inbox → Active:** 2026-09-04  
**Owner:** Python Dev  
**Duration:** 3 days  

## Spec

Define capability model and validate workflows don't use effects without declaring required capabilities.

### Acceptance Criteria
- [ ] Effect binding works for password-reset
- [ ] Unauthorized effect triggers ORIN-E010
- [ ] Persistence effect checks in place

## Implementation

[Code, PRs, commits go here]

## Review Gate

**Must pass before → archive:**
- [ ] All acceptance criteria verified
- [ ] Tests passing on Python 3.13+
- [ ] No regressions in M1 tests
- [ ] Code reviewed (2 eyes minimum)

**Sign-off:** [Language Designer]  
**Date:** 2026-09-07
```

**Tool:** Integrate with GitHub Issues or markdown task file in `tasks/`.

#### 3.7 Grill Me for User Research (M7)

**When:** Conducting 10 user sessions  
**How:** Run calibrated interview; adapt pressure level  
**Interview flow:**

```
Session Start
  → "How much do you know about intent-based programming?" [beginner/working/expert]
  → "How hard should I push on design decisions?" [soft/normal/hard]

Question 1: "Why did you choose password-reset as your first Orin program?"
  → Recommended answers: [X, Y, Z]
  → Follow-up options: [clarify, dig deeper, move on]

Question 2: "What was the hardest part about writing the intent spec?"
  → (Adapted based on their knowledge level)

...
```

**Tool:** Run `vendor/skills/scripts/grill-me.mjs` with interview template.

#### 3.8 Last 20% for MVP Release (M4)

**When:** End-to-end demo preparation  
**How:** Ensure golden path is smooth; all polish complete  
**Checklist:**

```markdown
# Last 20% Audit: MVP Release

## Content & IA
- [ ] README has clear "5-minute quickstart"
- [ ] Examples folder has well-named files
- [ ] Docs linked from everywhere relevant
- [ ] No "coming soon" or "TODO" in user-facing text

## First Run Experience
- [ ] Clone repo → first command works
- [ ] Error messages are helpful (point to docs)
- [ ] No hidden prerequisites (Python 3.13? TypeScript?)
- [ ] Demo script runs end-to-end without intervention

## Defaults & Golden Path
- [ ] Password-reset example is THE example (not buried)
- [ ] Both backends generate without flags (sensible defaults)
- [ ] Evidence records appear in obvious location
- [ ] Equivalence report human-readable

## Experiential Details
- [ ] Syntax highlighting in VS Code works (no copy-paste)
- [ ] Error codes (ORIN-EXXX) are documented
- [ ] Diagnostic messages are actionable
- [ ] Output layout is clean (logs, evidence, artifacts grouped)

## Walk-through as User
- [ ] Open password-reset.orin in VS Code
- [ ] Run "Analyze Current File" → no errors (Milestone 1 ✓)
- [ ] Run examples → all pass (Milestone 2 ✓)
- [ ] Generate backends → no flags needed (Milestone 3 ✓)
- [ ] View evidence → understand what ran (Milestone 4 ✓)
- [ ] Read walkthrough doc → get full story
```

---

## Concrete Implementation: First Three Skills

### 1. Caveman (Immediate Impact)

```python
# implementations/python/caveman_integration.py
"""Compress Orin diagnostic messages and proposal descriptions."""

from pathlib import Path
from vendor.skills.skills.caveman import SKILL_PROMPT

def compress_diagnostic(diagnostic):
    """Compress error message while preserving error code and location."""
    if diagnostic.code == "ORIN-E041":
        # Keep this one explicit (consequential)
        return diagnostic.message
    
    # Compress others
    original = diagnostic.message
    # Apply SKILL_PROMPT (full intensity)
    compressed = compress_text(original, intensity="full")
    
    return f"{diagnostic.code}: {compressed}"

def compress_proposal(proposal_dict):
    """Make AI proposals terse but clear."""
    description = proposal_dict["description"]
    affected_objects = proposal_dict["affected_objects"]
    
    # Caveman style
    caveman_desc = compress_text(description, intensity="full")
    
    return {
        **proposal_dict,
        "terse_description": caveman_desc,
        "affected_objects": affected_objects,
        "token_savings": len(description.split()) - len(caveman_desc.split())
    }
```

**Integration point:** Apply in `implementations/python/diagnostics.py` when emitting errors.

### 2. Junior-to-Senior (Quality Gate)

```python
# implementations/typescript/SENIOR-REVIEW-CHECK.ts
/**
 * Post-generation review checklist.
 * Must pass before M4 exit gate.
 */

import { readFileSync } from "fs";
import { execSync } from "child_process";

interface ReviewResult {
  passed: boolean;
  findings: string[];
  severity: "blocker" | "warning" | "info";
}

async function seniorReview(): Promise<ReviewResult> {
  const findings: string[] = [];
  
  // Check 1: Interfaces committed
  const src = readFileSync("src/types.ts", "utf-8");
  const anyCount = (src.match(/:\s*any/g) || []).length;
  if (anyCount > 0) {
    findings.push(`⚠️ Found ${anyCount} 'any' types. Specify interfaces explicitly.`);
  }
  
  // Check 2: Versions explicit
  const pkg = JSON.parse(readFileSync("package.json", "utf-8"));
  const locked = execSync("npm list --locked").toString().includes("dependencies ok");
  if (!locked) {
    findings.push("⚠️ Dependencies not locked. Run 'npm ci' to ensure reproducibility.");
  }
  
  // Check 3: Error contracts documented
  const effectHandlers = src.match(/catch\s*\(/g)?.length || 0;
  const errorDocs = src.match(/\/\/\s*Error:/g)?.length || 0;
  if (errorDocs < effectHandlers * 0.8) {
    findings.push(`⚠️ Only ${errorDocs}/${effectHandlers} error cases documented.`);
  }
  
  // Check 4: Evidence linked
  if (!src.includes("evidence")) {
    findings.push("❌ BLOCKER: Generated code doesn't link to evidence records.");
  }
  
  return {
    passed: findings.filter(f => f.startsWith("❌")).length === 0,
    findings,
    severity: findings.some(f => f.startsWith("❌")) ? "blocker" : "warning"
  };
}

// Run before M4 exit
if (require.main === module) {
  seniorReview().then(result => {
    console.log(`Senior Review: ${result.passed ? "✅ PASS" : "❌ FAIL"}`);
    result.findings.forEach(f => console.log(f));
    process.exit(result.passed ? 0 : 1);
  });
}
```

**Integration point:** Add to CI/CD as gate before merging M3 work.

### 3. Context Canary (Health Check)

```python
# implementations/python/session_health.py
"""Monitor long human-AI sessions for context degradation."""

from vendor.skills.skills.context_canary import ContextCanary
from dataclasses import dataclass
import json
from datetime import datetime

@dataclass
class SessionMetrics:
    user_name: str
    turn_number: int
    tokens_used: int
    tokens_available: int
    model_name: str
    timestamp: str

def check_session_health(metrics: SessionMetrics) -> tuple[str, str]:
    """
    Check health. Return (status, message).
    status: "healthy" | "degraded" | "critical"
    """
    canary = ContextCanary()
    
    signal = canary.signal(
        user_name=metrics.user_name,
        turn_count=metrics.turn_number,
        context_used=metrics.tokens_used,
        context_limit=metrics.tokens_available,
        model=metrics.model_name
    )
    
    if signal.status == "critical":
        return "critical", (
            f"🚨 CRITICAL: {metrics.tokens_available - metrics.tokens_used} tokens left. "
            f"Recommend checkpoint + fresh session. Last {metrics.turn_number} turns at risk."
        )
    elif signal.status == "degraded":
        return "degraded", (
            f"⚠️ DEGRADED: {signal.compaction_risk}% risk of silent context loss. "
            f"Monitor next 3 turns; fresh session after turn {metrics.turn_number + 5}."
        )
    else:
        return "healthy", f"✅ Session healthy. {metrics.tokens_available - metrics.tokens_used} tokens remaining."

# Usage in authoring loop (M6+)
def human_ai_authoring_turn(user_input: str, session_state: dict):
    # ... process user input ...
    
    # Health check every turn
    metrics = SessionMetrics(
        user_name=session_state["user"],
        turn_number=session_state["turn"],
        tokens_used=session_state["usage"]["input_tokens"] + session_state["usage"]["output_tokens"],
        tokens_available=200000,  # Model limit
        model_name="claude-3.5-sonnet",
        timestamp=datetime.now().isoformat()
    )
    
    status, message = check_session_health(metrics)
    
    if status in ["degraded", "critical"]:
        print(message)
        if status == "critical":
            # Trigger checkpoint flow
            checkpoint_and_reanchor(session_state)
    
    return assistant_response
```

---

## Git Submodule Maintenance

### Update Skills

```bash
cd vendor/skills
git pull origin main
cd ../..
git add vendor/skills
git commit -m "Update Julius Skills to latest version"
```

### Version Pin (Recommended)

Keep a specific skills version in `.gitmodules`:

```ini
[submodule "vendor/skills"]
    path = vendor/skills
    url = https://github.com/JuliusBrussee/skills.git
    branch = v1  # Pin to stable branch
```

---

## Skills Activation Checklist

- [ ] Add submodule: `git submodule add https://github.com/JuliusBrussee/skills.git vendor/skills`
- [ ] Create `.orin/skills-config.yaml` (above)
- [ ] Implement Caveman integration (diagnostics + proposals)
- [ ] Implement Junior-to-Senior (CI/CD review gate)
- [ ] Implement Context Canary (session health check)
- [ ] Add Interface Kit DESIGN.md reference
- [ ] Add Deslopify post-processing to docs generation
- [ ] Add Loop Factory task templates
- [ ] Add Grill Me interview script for M7
- [ ] Add Last 20% checklist to M4
- [ ] Document in README: "This project uses Julius Skills for AI efficiency"
- [ ] Test locally: all skills load and integrate correctly
- [ ] Add CI/CD: verify submodule initialized on clone

---

## Expected Efficiency Gains

| Metric | Before Skills | After Skills | Gain |
|--------|--------------|--------------|------|
| Proposal description tokens | 120 | 35 | 71% ↓ |
| Code review turnaround | 2-3 days | Same-day (automated gate) | 2-3x faster |
| Session health visibility | None | Every turn | 100% visible |
| Generated code polish | Demo-quality | Production-ready | +3-4 levels |
| User research efficiency | Unstructured | Calibrated pressure | 2x better insights |
| Document quality | Generic AI | Human-sounding | +2 grades |

---

**Next action:** Confirm submodule approach; then implement first 3 skills (Caveman, Junior-to-Senior, Context Canary) before M1 start.

