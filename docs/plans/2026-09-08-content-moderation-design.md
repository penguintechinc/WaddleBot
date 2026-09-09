# Content Moderation Design Specification

**Status:** DRAFT — for review, not implementation.

---

## 1. Overview

**Intent:** Classify inbound chat messages for harmful content (slurs, hate speech, harassment, etc.), apply reputation hits and optional enforcement (timeout/warn), with community-admin control over which categories are active.

Key properties:
- **Community-controlled:** each community opts into specific moderation categories, all OFF by default
- **Reputation-first:** every matched classification applies a reputation hit to the user (global + community-scoped)
- **Optional enforcement:** reputation hit is standalone; community may also enable timeout/warn for the category
- **Pluggable classifier:** swap between local Ollama and WaddleAI without changing the gate/config/flow
- **Graceful degradation:** missing WaddleAI does not crash; basic (local) categories keep working

---

## 2. Flow (per inbound chat message)

```
[inbound chat message]
          ↓
   classify(message, enabled_categories)
          ↓
     matched category?
    ╱          ╲
  YES           NO
   ↓            ↓
apply reputation hit    pass through
(global + community)          ↓
   ↓                       [next stage]
category's filter
   ON?
  ╱  ╲
ON   OFF
 ↓    ↓
ALSO  only reputation
timeout/warn hit
 ↓
[warn user + timeout]
 ↓
[next stage]
```

Reputation hit always applied (if matched); enforcement (timeout/warn) only if community has that category's filter enabled.

---

## 3. Config Model

**Per-community settings** (in `communities` row, or a new `community_moderation_config` table):
- Which category filters are enabled/enforced: `hate_speech_filter`, `harassment_filter`, `slur_filter`, `spam_filter`, etc. (booleans, all OFF by default)
- Per-category reputation weight: how many points a match deducts from community rep (float, 0.0–1.0 scale)
- Optional: confidence threshold gating enforcement (e.g., only timeout if classifier confidence ≥ 0.75)

**Per-tenant settings** (in `tenants` row, or a new `tenant_moderation_config` table):
- Per-category global reputation weight: how many points a match deducts from global score
- Which advanced/security packs are available (tied to license tier; see § 5)

**Where it lives in code:** `core/svc_process/config.py` (or its successor) holds the defaults and loads/validates these settings at startup; per-message classification passes the resolved config to the classifier.

---

## 4. Execution: Where It Runs

**svc-process stage gate** — all inbound chat messages pass through a content-moderation stage gate *before* any other process-stage bundle sees the message. The gate:
1. Fetches enabled categories for this message's (tenant, community)
2. Calls `classifier.classify(message, enabled_categories)` → returns `{category: str, confidence: float}` or `None`
3. If matched: applies reputation hit (always), then checks if that category's filter is ON (if yes: also applies timeout/warn)
4. Publishes the message (possibly timeout-tagged) to the next stream

No svc-process bundle touches a message if the moderation gate hasn't run first. The gate is not a bundle itself; it is a mandatory stage-runner gate, like `resolve_apps` or tenant-scoping, that runs before bundle dispatch.

---

## 5. ClassificationProvider Interface

Pluggable, two implementations:

```python
class ClassificationProvider(ABC):
    """Classify a message for harmful content."""
    
    async def classify(
        self,
        message: str,
        enabled_categories: Set[str],  # {"hate_speech", "harassment", ...}
        *,
        tenant_id: int,
        community_id: int,
    ) -> Optional[Classification]:
        """
        Returns Classification (category, confidence, severity) or None if no match.
        Enabled categories that do not match return None (no false positives logged as matches).
        """
        pass


@dataclass
class Classification:
    category: str           # "hate_speech", "harassment", etc.
    confidence: float       # 0.0–1.0, model-specific calibration
    severity: str           # "low" | "medium" | "high"
```

### 5.1 LocalOllamaClassifier

Runs local Ollama; default model `shieldgemma:2b` (purpose-built moderation, fast, calibrated confidence).

```python
class LocalOllamaClassifier(ClassificationProvider):
    """Local Ollama-based classification."""
    
    def __init__(self, ollama_host: str, model: str = "shieldgemma:2b"):
        self.ollama_host = ollama_host  # e.g., "http://ollama:11434"
        self.model = model  # configurable; fallback "gemma4:e4b" for higher accuracy
```

**Properties:**
- No external dependency (runs offline, no WaddleAI needed)
- Fast, suitable for per-message hot path (sub-500ms target)
- Model configurable at startup
- Fallback: route confidence-borderline cases to `gemma4:e4b` for a second opinion (config knob)

### 5.2 WaddleAIClassifier

Routes to WaddleAI; passes enabled categories in the `X-CLASSIFICATION-BUNDLES` header.

```python
class WaddleAIClassifier(ClassificationProvider):
    """Delegates to WaddleAI for advanced/security classifications."""
    
    async def classify(self, message: str, enabled_categories: Set[str], **ctx):
        # POST /api/v1/classify
        # headers: X-CLASSIFICATION-BUNDLES: hate_speech,harassment,security-toxicity
        # body: {message, confidence_threshold, ...}
        # Returns WaddleAI's classification (or 404/error if bundle not available)
```

**Properties:**
- Advanced and security moderation packs available only via WaddleAI
- Graceful degradation: if WaddleAI is unreachable, those packs silently skip (category treated as disabled, not an error)
- Per-community enabled categories determine which bundles are sent in the request header

---

## 6. Pack Tiers

| Tier | Categories | Provider | Availability | Prerequisite |
|---|---|---|---|---|
| **Basic** | `hate_speech`, `basic_harassment`, `slurs` | LocalOllamaClassifier (shieldgemma:2b) | In waddlebot, standalone, no WaddleAI needed | None |
| **Advanced** | `targeted_harassment`, `doxxing_risk`, `coordinated_abuse` | WaddleAIClassifier | Only when WaddleAI is available | WaddleAI connection |
| **Security** | `prompt_injection`, `bot_evasion_attempts` | WaddleAIClassifier | Only when WaddleAI is available | WaddleAI connection |

**Graceful degradation:**
- Basic categories always work (local Ollama)
- Advanced/Security categories: if a community enables one and WaddleAI is unavailable, the category is silently skipped (logs a warning, does not crash, category filter treated as OFF)
- User docs MUST state that Advanced/Security require WaddleAI

**Core tenet:** "Run independently, better together" — waddlebot moderation works without WaddleAI; WaddleAI makes it better by adding advanced packs.

---

## 7. Hard Dependency: Reputation Accrual (#299)

**CRITICAL BLOCKER:** Reputation *accrual* is currently broken. `reputation_service.py` writes to a nonexistent `community_members.hub_user_id` column; the real column is `user_id`. 

- Reputation *display* works (reading existing scores)
- Reputation *accrual* does not (the hit is lost)

**Prerequisite:** Fix #299 first. The "apply reputation hit" step in § 2 does nothing until #299 is resolved.

---

## 8. Licensing & Tier Angle

**Basic moderation** (local Ollama) is available on all tiers (Free, Professional, Enterprise).

**Advanced/Security moderation** (WaddleAI bundles) is **Enterprise-gated** — requires `license.penguintech.io` entitlement check. A community on Free/Professional tiers cannot enable Advanced/Security categories (UI enforcement + API rejection on config update).

**Consumable licensing angle:** WaddleAI's moderation is offered as a metered/consumable bundle surface (tokens or classifications per month). This design does not finalize the licensing mechanics, but notes that:
- Basic moderation has no per-message cost (local compute)
- Advanced/Security moderation incurs WaddleAI API cost, subject to metering
- Per-tenant provisioning (which Advanced packs a tenant can use) is a licensing decision

Leave the full licensing design to the integrating-license-server skill and the license team.

---

## 9. Docs Requirement

User-facing documentation MUST list:
- Basic moderation categories and what they catch
- Which tiers can enable each category (Basic = all tiers; Advanced/Security = Enterprise only)
- Configuration instructions (per-community toggle, confidence threshold, if supported)
- Reputation deduction amounts per category (once decided in § 10)
- WaddleAI dependency statement for Advanced/Security

---

## 10. Open Questions (Not Decided Here)

| # | Question | Why open |
|---|---|---|
| 1 | **Reputation delta math** | exact points deducted per category/severity; whether a single message can match multiple categories and stack deltas; whether escalating repeated offenses adjust deltas up |
| 2 | **Confidence thresholds** | threshold at which enforcement (timeout/warn) is applied; whether reputation hit has a separate, lower threshold; whether to allow per-community tuning |
| 3 | **Repeat offense handling** | whether the second/third matched message in N hours escalates the action (longer timeout, mute, kick) or just applies the same hit |
| 4 | **Admin UI & representations** | how community admins view/edit per-category filter toggles, reputation weights, thresholds; where this lives (hub-webui or embedded in waddlebot-admin) |
| 5 | **Sync vs. async classification** | given the 1s per-message SLA, does every message go through the classifier synchronously (blocks the pipeline if classifier is slow), or do we classify async and apply hits retroactively; if async, how does a retroactive reputation hit interact with user experience (they post → no immediate timeout, timeout appears later?) |
| 6 | **Timeout mapping per platform** | what "timeout" means for Twitch IRC (actual IRC `/timeout` command?) vs. Discord (mute role, message delete?); who executes it (svc-action or the ingester?) |
| 7 | **Audit logging** | whether moderation decisions are logged (which messages matched, why, what action was taken, who enabled that category) for community admin review; format and retention |
| 8 | **Opt-out for non-English** | whether non-English text is classified at all (shieldgemma and other models may degrade on non-English); whether to disable moderation for communities with a non-English language setting |

---

## 11. Relationships

**Trims #304** (WaddleAI prompt-injection defense, output-safety, RAG heavy-lifting): Inbound content moderation is waddlebot's responsibility; WaddleAI handles the advanced/security packs and owns prompt-injection detection on its own. This design carves out the inbound message moderation slice — waddlebot owns it end-to-end for basic, delegates advanced packs to WaddleAI.

**Depends on #299** (reputation accrual fix): reputation writing is currently broken; prerequisite to any moderation feature that applies reputation hits.

**Touches forum/ingest work**: Moderation packs are invoked at the ingest stage boundary (all messages), so scheduling/resource planning for classifier throughput affects ingest design.

---

## 12. Implementation Phases (Sketch)

**P1:** Fix #299 (reputation accrual), stub the moderation gate in svc-process (always passes through, logs enabled categories), implement LocalOllamaClassifier against a test dataset of slurs/hate-speech.

**P2:** Implement WaddleAIClassifier (requires WaddleAI API contract finalized), graceful degradation (silent skip if unreachable), enable Advanced/Security category toggles in community config.

**P3:** Per-community UI for filter toggles, weight tuning, confidence thresholds (hub-webui or waddlebot-admin).

**P4:** Audit logging, per-platform timeout/warn action handlers, repeat-offense escalation logic.

