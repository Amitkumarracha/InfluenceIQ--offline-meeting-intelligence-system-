"""
Decision-linked participant influence analysis — Phase 11.

Consumes:
  - EventExtractionResult    (Phase 8 events JSON)
  - EvidenceExtractionResult (Phase 8 evidence JSON)
  - DecisionResult           (Phase 9 decisions JSON)
  - InteractionResult        (Phase 10 interactions JSON)

Produces:
  - InfluenceResult          : meeting-level and decision-level scores
  - Baselines                : speaking-time and event-count baselines

Core research principle
-----------------------
  Conversational dominance  ≠  Decision influence

Speaking time is intentionally NOT the dominant component.
A participant may speak infrequently but have high decision-linked
influence if they introduce proposals that become decisions, provide
critical evidence, or raise objections that trigger revisions.

Scoring model (transparent, weighted sum)
-----------------------------------------
Seven interpretable feature categories:

  1. proposal_contribution    — decision-linked proposals
  2. evidence_contribution    — decision-linked evidence events
  3. objection_contribution   — objections followed by a revision
  4. revision_contribution    — revisions that are part of a decision chain
  5. decision_contribution    — direct participation in confirmed decisions
  6. interaction_contribution — decision-linked interactions from Phase 10
  7. slide_grounded_contribution — contributions grounded to slides

Influence =
  w_proposal  * proposal_contribution  (normalised)
+ w_evidence  * evidence_contribution  (normalised)
+ w_objection * objection_contribution (normalised)
+ w_revision  * revision_contribution  (normalised)
+ w_decision  * decision_contribution  (normalised)
+ w_interact  * interaction_contribution (normalised)
+ w_slide     * slide_grounded_contribution (normalised)

Normalisation
-------------
Each raw feature value is divided by the maximum value across all
participants (max-normalisation).  If the maximum is zero, all
normalised values are set to 0.0 safely (no NaN).

Initial prototype weights (NOT validated)
-----------------------------------------
  proposal:      0.15
  evidence:      0.20
  objection:     0.15
  revision:      0.20
  decision:      0.15
  interaction:   0.05
  slide_grounding: 0.10

All weights are configurable via config.yaml.

Baselines (stored separately, not mixed into proposed score)
------------------------------------------------------------
  B1  speaking_time          — total transcript segment duration
  B2  speaking_time_turns    — speaking time + turn count (normalised sum)
  B3  decision_event_count   — number of decision-linked events
  B4  decision_evidence_count — number of decision-linked evidence relations

Limitations (explicitly documented)
-------------------------------------
- Scores are analytical estimates based on observable meeting evidence.
- They do NOT establish causal truth.
- Human evaluation is required to validate rankings.
- Weights are prototype values; ablation and annotation studies are needed.
- Coreference is not resolved; the same topic may map to multiple decisions.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.meeting.decisions import Decision, DecisionResult, load_decisions_json
from src.meeting.events import EventExtractionResult, MeetingEvent, load_events_json
from src.meeting.evidence import EvidenceExtractionResult, EvidenceRelation, load_evidence_json
from src.meeting.interaction import InteractionResult, load_interactions_json
from src.utils.config import get
from src.utils.logging import get_logger

logger = get_logger("meeting.influence")

# ---------------------------------------------------------------------------
# Default weights (prototype — not validated)
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {
    "proposal":      0.15,
    "evidence":      0.20,
    "objection":     0.15,
    "revision":      0.20,
    "decision":      0.15,
    "interaction":   0.05,
    "slide_grounding": 0.10,
}

FEATURE_KEYS: list[str] = list(DEFAULT_WEIGHTS.keys())


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FeatureVector:
    """
    Raw (un-normalised) feature counts for one participant.

    All values are counts or sums derived from meeting evidence.
    They are NOT influence scores until normalised and weighted.
    """
    participant: str
    proposal_contribution: float = 0.0
    evidence_contribution: float = 0.0
    objection_contribution: float = 0.0
    revision_contribution: float = 0.0
    decision_contribution: float = 0.0
    interaction_contribution: float = 0.0
    slide_grounded_contribution: float = 0.0

    # Ablation flags — set to False to zero-out a feature at score time
    use_proposal:       bool = True
    use_evidence:       bool = True
    use_objection:      bool = True
    use_revision:       bool = True
    use_decision:       bool = True
    use_interaction:    bool = True
    use_slide_grounding: bool = True

    def to_dict(self) -> dict[str, float]:
        return {
            "proposal_contribution":      self.proposal_contribution,
            "evidence_contribution":      self.evidence_contribution,
            "objection_contribution":     self.objection_contribution,
            "revision_contribution":      self.revision_contribution,
            "decision_contribution":      self.decision_contribution,
            "interaction_contribution":   self.interaction_contribution,
            "slide_grounded_contribution": self.slide_grounded_contribution,
        }


@dataclass
class DecisionContribution:
    """A participant's decision-linked contribution record for one decision."""
    decision_id: str
    contribution_score: float
    roles: list[str]
    supporting_events: list[str]


@dataclass
class ParticipantInfluence:
    """
    Influence analysis result for one participant.

    influence_score is an analytical estimate, NOT a causal truth.
    """
    participant: str
    influence_score: float          # weighted normalised score in [0, 1]
    rank: int
    normalised_features: dict[str, float]   # normalised, pre-weighting
    raw_features: dict[str, float]          # raw counts
    decision_contributions: list[DecisionContribution]
    supporting_decisions: list[str]
    supporting_events: list[str]
    explanation: list[str]


@dataclass
class BaselineScores:
    """Baseline scores for one participant (stored separately)."""
    participant: str
    speaking_time: float               # B1 — raw seconds
    speaking_time_norm: float          # B1 normalised
    speaking_time_turns: float         # B2 — time + turns combined (normalised)
    decision_event_count: int          # B3
    decision_event_count_norm: float   # B3 normalised
    decision_evidence_count: int       # B4
    decision_evidence_count_norm: float  # B4 normalised


@dataclass
class InfluenceResult:
    """Container for the full Phase 11 influence analysis."""
    meeting_id: str
    method: dict[str, Any]              # metadata about the scoring approach
    participants: list[ParticipantInfluence]
    baselines: list[BaselineScores]

    def by_rank(self) -> list[ParticipantInfluence]:
        return sorted(self.participants, key=lambda p: p.rank)

    def for_participant(self, speaker: str) -> ParticipantInfluence | None:
        return next((p for p in self.participants if p.participant == speaker), None)


# ---------------------------------------------------------------------------
# Weight loading and validation
# ---------------------------------------------------------------------------

def _load_weights() -> dict[str, float]:
    """
    Load influence weights from config.yaml.

    Falls back to DEFAULT_WEIGHTS for any missing key.
    Normalises weights to sum to 1.0 if they do not already.
    """
    cfg_weights = get("influence.weights") or {}
    weights: dict[str, float] = {}
    for key in FEATURE_KEYS:
        raw = cfg_weights.get(key, DEFAULT_WEIGHTS[key])
        try:
            val = float(raw)
        except (TypeError, ValueError):
            logger.warning("Invalid weight for '%s': %r — using default %.2f", key, raw, DEFAULT_WEIGHTS[key])
            val = DEFAULT_WEIGHTS[key]
        weights[key] = max(0.0, val)   # weights must be non-negative

    total = sum(weights.values())
    if total <= 0.0:
        logger.warning("All influence weights are zero — using defaults.")
        weights = dict(DEFAULT_WEIGHTS)
        total = sum(weights.values())

    # Normalise to sum = 1
    return {k: v / total for k, v in weights.items()}


# ---------------------------------------------------------------------------
# Normalisation helper
# ---------------------------------------------------------------------------

def _max_normalise(values: dict[str, float]) -> dict[str, float]:
    """
    Divide each value by the maximum.  Returns all-zero dict if max == 0.

    Never produces NaN or negative values.
    """
    max_val = max(values.values(), default=0.0)
    if max_val <= 0.0:
        return {k: 0.0 for k in values}
    return {k: v / max_val for k, v in values.items()}


def _normalise_feature_across_participants(
    vectors: dict[str, FeatureVector],
    feature: str,
) -> dict[str, float]:
    """Return {speaker: normalised_value} for one feature across all participants."""
    raw = {sp: getattr(vec, feature) for sp, vec in vectors.items()}
    return _max_normalise(raw)


# ---------------------------------------------------------------------------
# Feature extraction helpers
# ---------------------------------------------------------------------------

def _event_index(events: list[MeetingEvent]) -> dict[str, MeetingEvent]:
    return {e.event_id: e for e in events}


def _decision_event_ids(decision: Decision) -> set[str]:
    """All event_ids that belong to this decision cluster."""
    ids: set[str] = set()
    if decision.proposal:
        ids.add(decision.proposal["event_id"])
    for item in decision.discussion:
        ids.add(item["event_id"])
    for item in decision.revisions:
        ids.add(item["event_id"])
    for item in decision.agreements:
        ids.add(item["event_id"])
    if decision.final_decision:
        ids.add(decision.final_decision["event_id"])
    return ids


def _revision_event_ids(decision: Decision) -> set[str]:
    return {r["event_id"] for r in decision.revisions}


def _objection_triggers_revision(
    objection_ev: MeetingEvent,
    decision: Decision,
    ev_index: dict[str, MeetingEvent],
) -> bool:
    """
    Return True if an objection event appears to have triggered a revision.

    Heuristic: a revision exists in the same decision cluster AND
    the revision occurs after the objection temporally.

    This is NOT a causal claim — it is a temporal association.
    """
    revisions = decision.revisions
    if not revisions:
        return False
    for r in revisions:
        r_ev = ev_index.get(r["event_id"])
        if r_ev is not None and r_ev.start > objection_ev.start:
            return True
    return False


def _evidence_contributes_to_revision(
    evidence_ev: MeetingEvent,
    decision: Decision,
    ev_index: dict[str, MeetingEvent],
) -> bool:
    """True if the decision has a revision occurring after this evidence event."""
    for r in decision.revisions:
        r_ev = ev_index.get(r["event_id"])
        if r_ev is not None and r_ev.start > evidence_ev.start:
            return True
    return False


# ---------------------------------------------------------------------------
# Core feature extraction
# ---------------------------------------------------------------------------

def extract_features(
    event_result: EventExtractionResult,
    evidence_result: EvidenceExtractionResult,
    decision_result: DecisionResult,
    interaction_result: InteractionResult,
) -> dict[str, FeatureVector]:
    """
    Extract raw feature vectors for each participant.

    Returns {speaker: FeatureVector}.
    """
    events = event_result.events
    ev_index = _event_index(events)
    decisions = decision_result.decisions

    # Initialise vectors for every speaker seen in events
    all_speakers = sorted({e.speaker for e in events})
    vectors: dict[str, FeatureVector] = {
        sp: FeatureVector(participant=sp) for sp in all_speakers
    }

    # Build a map: event_id → decision_id
    event_to_decision: dict[str, str] = {}
    for d in decisions:
        for eid in _decision_event_ids(d):
            event_to_decision[eid] = d.decision_id

    # Build set of event_ids that are revisions, grouped by decision
    revision_ids_by_decision: dict[str, set[str]] = {
        d.decision_id: _revision_event_ids(d) for d in decisions
    }

    # ---- Feature A: proposal_contribution ----
    # A proposal counts if it is part of a decision cluster.
    for d in decisions:
        if d.proposal:
            sp = d.proposal.get("speaker")
            if sp and sp in vectors:
                vectors[sp].proposal_contribution += 1.0
                # Extra credit if it became the final decision
                if d.final_decision and d.status == "confirmed":
                    vectors[sp].proposal_contribution += 1.0

    # ---- Feature B: evidence_contribution ----
    # Evidence events that are decision-linked; extra if grounded to a slide.
    for ev in events:
        if ev.event_type != "evidence":
            continue
        if ev.event_id not in event_to_decision:
            continue
        sp = ev.speaker
        if sp not in vectors:
            continue
        vectors[sp].evidence_contribution += 1.0
        if ev.slide_id is not None:
            vectors[sp].evidence_contribution += 0.5   # slide-grounded bonus

    # ---- Feature C: objection_contribution ----
    # Objections and disagreements that are decision-linked AND
    # are followed by a revision in the same decision cluster.
    for ev in events:
        if ev.event_type not in ("objection", "disagreement"):
            continue
        dec_id = event_to_decision.get(ev.event_id)
        if dec_id is None:
            continue
        decision = next((d for d in decisions if d.decision_id == dec_id), None)
        if decision is None:
            continue
        sp = ev.speaker
        if sp not in vectors:
            continue
        # Base credit for a decision-linked objection
        vectors[sp].objection_contribution += 0.5
        # Extra if it appears to have triggered a revision
        if _objection_triggers_revision(ev, decision, ev_index):
            vectors[sp].objection_contribution += 1.0

    # ---- Feature D: revision_contribution ----
    # Revisions within confirmed/probable decisions.
    for d in decisions:
        if d.status not in ("confirmed", "probable"):
            continue
        for r in d.revisions:
            rev_ev = ev_index.get(r["event_id"])
            if rev_ev is None:
                continue
            sp = rev_ev.speaker
            if sp not in vectors:
                continue
            vectors[sp].revision_contribution += 1.0

    # ---- Feature E: decision_contribution ----
    # Direct participation in confirmed/probable decisions.
    for d in decisions:
        cluster_ids = _decision_event_ids(d)
        for eid in cluster_ids:
            ev = ev_index.get(eid)
            if ev is None:
                continue
            sp = ev.speaker
            if sp not in vectors:
                continue
            if d.status == "confirmed":
                vectors[sp].decision_contribution += 1.0
            elif d.status == "probable":
                vectors[sp].decision_contribution += 0.5

    # ---- Feature F: interaction_contribution ----
    # Decision-linked interactions from Phase 10 (source speaker credit).
    for intr in interaction_result.interactions:
        if intr.related_decision_id is None:
            continue
        sp = intr.source_speaker
        if sp not in vectors:
            continue
        vectors[sp].interaction_contribution += 1.0

    # ---- Feature G: slide_grounded_contribution ----
    # Any decision-linked event that is grounded to a slide.
    for ev in events:
        if ev.slide_id is None:
            continue
        if ev.event_id not in event_to_decision:
            continue
        sp = ev.speaker
        if sp not in vectors:
            continue
        vectors[sp].slide_grounded_contribution += 1.0

    return vectors


# ---------------------------------------------------------------------------
# Baseline extraction
# ---------------------------------------------------------------------------

def extract_baselines(
    event_result: EventExtractionResult,
    evidence_result: EvidenceExtractionResult,
    decision_result: DecisionResult,
) -> dict[str, BaselineScores]:
    """
    Compute baseline scores for all participants.

    B1: speaking time (sum of event durations as proxy)
    B2: speaking time + number of speaking turns (normalised sum / 2)
    B3: decision-linked event count
    B4: decision-linked evidence relation count

    NOTE: These use events as a proxy for speaking time.
    For a more accurate speaking-time baseline the raw transcript segments
    (Phase 5 output) should be used.  This is documented as a limitation.
    """
    events = event_result.events
    all_speakers = sorted({e.speaker for e in events})

    # B1: speaking time (sum of event durations per speaker)
    speaking_time: dict[str, float] = {sp: 0.0 for sp in all_speakers}
    turn_count: dict[str, int] = {sp: 0 for sp in all_speakers}
    for ev in events:
        sp = ev.speaker
        if sp in speaking_time:
            speaking_time[sp] += ev.end - ev.start
            turn_count[sp] += 1

    # B3: decision-linked event count
    event_to_decision: dict[str, str] = {}
    for d in decision_result.decisions:
        for eid in _decision_event_ids(d):
            event_to_decision[eid] = d.decision_id

    dec_event_count: dict[str, int] = {sp: 0 for sp in all_speakers}
    for ev in events:
        if ev.event_id in event_to_decision and ev.speaker in dec_event_count:
            dec_event_count[ev.speaker] += 1

    # B4: decision-linked evidence count
    dec_evidence_count: dict[str, int] = {sp: 0 for sp in all_speakers}
    for rel in evidence_result.relations:
        if rel.source_event_id.startswith("slide:"):
            continue
        src_ev = next((e for e in events if e.event_id == rel.source_event_id), None)
        if src_ev is None:
            continue
        if rel.target_event_id in event_to_decision:
            sp = src_ev.speaker
            if sp in dec_evidence_count:
                dec_evidence_count[sp] += 1

    # Normalise
    st_norm = _max_normalise(speaking_time)
    tc_norm = _max_normalise({sp: float(turn_count[sp]) for sp in all_speakers})
    b2_raw = {sp: (st_norm[sp] + tc_norm[sp]) / 2.0 for sp in all_speakers}
    dec_ev_norm = _max_normalise({sp: float(dec_event_count[sp]) for sp in all_speakers})
    dec_evid_norm = _max_normalise({sp: float(dec_evidence_count[sp]) for sp in all_speakers})

    return {
        sp: BaselineScores(
            participant=sp,
            speaking_time=speaking_time[sp],
            speaking_time_norm=st_norm[sp],
            speaking_time_turns=b2_raw[sp],
            decision_event_count=dec_event_count[sp],
            decision_event_count_norm=dec_ev_norm[sp],
            decision_evidence_count=dec_evidence_count[sp],
            decision_evidence_count_norm=dec_evid_norm[sp],
        )
        for sp in all_speakers
    }


# ---------------------------------------------------------------------------
# Decision-level contribution
# ---------------------------------------------------------------------------

def compute_decision_contributions(
    speaker: str,
    decisions: list[Decision],
    ev_index: dict[str, MeetingEvent],
    normalised_features: dict[str, float],
) -> list[DecisionContribution]:
    """
    For each decision, compute this speaker's contribution score and roles.

    The contribution score is a simple average of the speaker's normalised
    features that are relevant to the decision.  It is NOT a separate
    scoring pass — it reuses the meeting-level normalised features as a
    proxy.  A proper per-decision score would require per-decision
    normalisation, which is reserved for future work.
    """
    contributions: list[DecisionContribution] = []

    for d in decisions:
        cluster_ids = _decision_event_ids(d)
        speaker_events = [
            ev_index[eid]
            for eid in cluster_ids
            if eid in ev_index and ev_index[eid].speaker == speaker
        ]
        if not speaker_events:
            continue

        # Roles in this decision
        roles: list[str] = []
        if d.proposal and d.proposal.get("speaker") == speaker:
            roles.append("proposer")
        for r in d.revisions:
            rev_ev = ev_index.get(r["event_id"])
            if rev_ev and rev_ev.speaker == speaker:
                roles.append("reviser")
        for a in d.agreements:
            ag_ev = ev_index.get(a["event_id"])
            if ag_ev and ag_ev.speaker == speaker:
                roles.append("supporter")
        if d.final_decision:
            fd_ev = ev_index.get(d.final_decision["event_id"])
            if fd_ev and fd_ev.speaker == speaker:
                roles.append("final_decision_maker")
        # Objector role
        for ev in speaker_events:
            if ev.event_type in ("objection", "disagreement") and "objector" not in roles:
                roles.append("objector")
        if d.proposal and any(ev.event_type == "evidence" for ev in speaker_events):
            if "evidence_provider" not in roles:
                roles.append("evidence_provider")

        # Contribution score: fraction of cluster events belonging to this speaker,
        # weighted by meeting-level normalised score.
        fraction = len(speaker_events) / max(1, len(cluster_ids))
        inf_score = sum(normalised_features.values()) / max(1, len(normalised_features))
        contrib_score = round(fraction * inf_score, 4)

        contributions.append(DecisionContribution(
            decision_id=d.decision_id,
            contribution_score=contrib_score,
            roles=sorted(set(roles)),
            supporting_events=[ev.event_id for ev in speaker_events],
        ))

    return contributions


# ---------------------------------------------------------------------------
# Explanation generation
# ---------------------------------------------------------------------------

def _generate_explanation(
    speaker: str,
    norm_features: dict[str, float],
    raw_features: dict[str, float],
    decision_contribs: list[DecisionContribution],
    weights: dict[str, float],
) -> list[str]:
    """
    Generate human-readable explanation strings from actual feature values.

    All explanations are derived from data — nothing is fabricated.
    """
    lines: list[str] = []

    if norm_features.get("proposal_contribution", 0) > 0.4:
        n = int(raw_features.get("proposal_contribution", 0))
        lines.append(
            f"Introduced decision-linked proposals (raw contribution: {n:.1f}). "
            f"Normalised proposal score: {norm_features['proposal_contribution']:.2f}."
        )

    if norm_features.get("evidence_contribution", 0) > 0.3:
        n = raw_features.get("evidence_contribution", 0)
        lines.append(
            f"Provided evidence linked to decision formation (raw: {n:.1f}). "
            f"Normalised evidence score: {norm_features['evidence_contribution']:.2f}."
        )

    if norm_features.get("objection_contribution", 0) > 0.3:
        n = raw_features.get("objection_contribution", 0)
        lines.append(
            f"Raised objection(s) associated with proposal revisions (raw: {n:.1f}). "
            f"Normalised objection score: {norm_features['objection_contribution']:.2f}."
        )

    if norm_features.get("revision_contribution", 0) > 0.3:
        n = int(raw_features.get("revision_contribution", 0))
        lines.append(
            f"Contributed revision(s) within confirmed/probable decisions (count: {n})."
        )

    if norm_features.get("decision_contribution", 0) > 0.3:
        n = raw_features.get("decision_contribution", 0)
        lines.append(
            f"Directly participated in confirmed/probable decision clusters (raw: {n:.1f})."
        )

    if norm_features.get("slide_grounded_contribution", 0) > 0.3:
        n = int(raw_features.get("slide_grounded_contribution", 0))
        lines.append(
            f"Made {n} decision-linked contribution(s) grounded to presentation slides."
        )

    if norm_features.get("interaction_contribution", 0) > 0.3:
        n = int(raw_features.get("interaction_contribution", 0))
        lines.append(
            f"Initiated {n} decision-linked interaction(s) in the participant graph."
        )

    for dc in decision_contribs:
        if dc.contribution_score > 0 and dc.roles:
            role_str = ", ".join(dc.roles)
            lines.append(
                f"Played role(s) [{role_str}] in {dc.decision_id} "
                f"(decision-linked contribution score: {dc.contribution_score:.2f})."
            )

    if not lines:
        lines.append(
            "Insufficient decision-linked evidence to attribute meaningful contributions. "
            "Score reflects limited participation in tracked decision events."
        )

    return lines


# ---------------------------------------------------------------------------
# Core scoring
# ---------------------------------------------------------------------------

def compute_influence(
    event_result: EventExtractionResult,
    evidence_result: EvidenceExtractionResult,
    decision_result: DecisionResult,
    interaction_result: InteractionResult,
    weights: dict[str, float] | None = None,
    ablation_flags: dict[str, bool] | None = None,
) -> InfluenceResult:
    """
    Compute participant influence scores.

    Parameters
    ----------
    event_result       : Phase 8 events
    evidence_result    : Phase 8 evidence
    decision_result    : Phase 9 decisions
    interaction_result : Phase 10 interactions
    weights            : Feature weights (defaults to config / DEFAULT_WEIGHTS)
    ablation_flags     : {feature_key: bool} to disable individual features

    Returns
    -------
    InfluenceResult
    """
    if weights is None:
        weights = _load_weights()

    # Apply ablation flags
    if ablation_flags:
        for key, enabled in ablation_flags.items():
            if not enabled:
                weights = dict(weights)
                weights[key] = 0.0
        # Re-normalise after zeroing
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        else:
            weights = {k: 0.0 for k in FEATURE_KEYS}

    ev_index = _event_index(event_result.events)

    # Step 1: extract raw feature vectors
    vectors = extract_features(
        event_result, evidence_result, decision_result, interaction_result
    )

    all_speakers = sorted(vectors.keys())
    if not all_speakers:
        return InfluenceResult(
            meeting_id=event_result.meeting_id,
            method=_method_meta(weights),
            participants=[],
            baselines=[],
        )

    # Step 2: normalise each feature across participants
    norm_map: dict[str, dict[str, float]] = {}
    feature_attrs = [
        "proposal_contribution",
        "evidence_contribution",
        "objection_contribution",
        "revision_contribution",
        "decision_contribution",
        "interaction_contribution",
        "slide_grounded_contribution",
    ]
    feature_weight_keys = [
        "proposal", "evidence", "objection",
        "revision", "decision", "interaction", "slide_grounding",
    ]
    for attr, wkey in zip(feature_attrs, feature_weight_keys):
        raw_vals = {sp: getattr(vectors[sp], attr) for sp in all_speakers}
        norm_map[attr] = _max_normalise(raw_vals)

    # Step 3: compute weighted influence score
    scores: dict[str, float] = {}
    for sp in all_speakers:
        s = 0.0
        s += weights.get("proposal",      0.0) * norm_map["proposal_contribution"][sp]
        s += weights.get("evidence",      0.0) * norm_map["evidence_contribution"][sp]
        s += weights.get("objection",     0.0) * norm_map["objection_contribution"][sp]
        s += weights.get("revision",      0.0) * norm_map["revision_contribution"][sp]
        s += weights.get("decision",      0.0) * norm_map["decision_contribution"][sp]
        s += weights.get("interaction",   0.0) * norm_map["interaction_contribution"][sp]
        s += weights.get("slide_grounding", 0.0) * norm_map["slide_grounded_contribution"][sp]
        scores[sp] = round(s, 6)

    # Step 4: rank (1 = highest; ties share the same rank)
    sorted_speakers = sorted(all_speakers, key=lambda sp: scores[sp], reverse=True)
    ranks: dict[str, int] = {}
    current_rank = 1
    prev_score: float | None = None
    for i, sp in enumerate(sorted_speakers):
        if prev_score is None or scores[sp] < prev_score:
            current_rank = i + 1
        ranks[sp] = current_rank
        prev_score = scores[sp]

    # Step 5: baselines
    baseline_map = extract_baselines(event_result, evidence_result, decision_result)

    # Step 6: build ParticipantInfluence objects
    participants: list[ParticipantInfluence] = []
    for sp in all_speakers:
        vec = vectors[sp]
        raw_feat = vec.to_dict()
        norm_feat = {
            "proposal_contribution":       norm_map["proposal_contribution"][sp],
            "evidence_contribution":       norm_map["evidence_contribution"][sp],
            "objection_contribution":      norm_map["objection_contribution"][sp],
            "revision_contribution":       norm_map["revision_contribution"][sp],
            "decision_contribution":       norm_map["decision_contribution"][sp],
            "interaction_contribution":    norm_map["interaction_contribution"][sp],
            "slide_grounded_contribution": norm_map["slide_grounded_contribution"][sp],
        }

        dec_contribs = compute_decision_contributions(
            sp, decision_result.decisions, ev_index, norm_feat
        )

        supporting_decisions = sorted({dc.decision_id for dc in dec_contribs})
        supporting_events = sorted({
            eid
            for dc in dec_contribs
            for eid in dc.supporting_events
        })

        explanation = _generate_explanation(sp, norm_feat, raw_feat, dec_contribs, weights)

        participants.append(ParticipantInfluence(
            participant=sp,
            influence_score=scores[sp],
            rank=ranks[sp],
            normalised_features=norm_feat,
            raw_features=raw_feat,
            decision_contributions=dec_contribs,
            supporting_decisions=supporting_decisions,
            supporting_events=supporting_events,
            explanation=explanation,
        ))

    return InfluenceResult(
        meeting_id=event_result.meeting_id,
        method=_method_meta(weights),
        participants=participants,
        baselines=list(baseline_map.values()),
    )


def _method_meta(weights: dict[str, float]) -> dict[str, Any]:
    return {
        "type": "decision_linked_weighted_score",
        "normalization": "max",
        "weights": dict(weights),
        "disclaimer": (
            "Scores are analytical estimates based on observable meeting evidence. "
            "They do not establish causal truth. "
            "Human evaluation is required to validate rankings."
        ),
    }


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def _pi_to_dict(p: ParticipantInfluence) -> dict[str, Any]:
    return {
        "participant": p.participant,
        "influence_score": p.influence_score,
        "rank": p.rank,
        "features": p.normalised_features,
        "raw_features": p.raw_features,
        "decision_contributions": [
            {
                "decision_id": dc.decision_id,
                "contribution_score": dc.contribution_score,
                "roles": dc.roles,
                "supporting_events": dc.supporting_events,
            }
            for dc in p.decision_contributions
        ],
        "supporting_decisions": p.supporting_decisions,
        "supporting_events": p.supporting_events,
        "explanation": p.explanation,
    }


def _baseline_to_dict(b: BaselineScores) -> dict[str, Any]:
    return {
        "participant": b.participant,
        "B1_speaking_time_s": b.speaking_time,
        "B1_speaking_time_norm": b.speaking_time_norm,
        "B2_speaking_time_turns_norm": b.speaking_time_turns,
        "B3_decision_event_count": b.decision_event_count,
        "B3_decision_event_count_norm": b.decision_event_count_norm,
        "B4_decision_evidence_count": b.decision_evidence_count,
        "B4_decision_evidence_count_norm": b.decision_evidence_count_norm,
    }


def save_influence_json(result: InfluenceResult, output_path: Path) -> None:
    """Write InfluenceResult to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "meeting_id": result.meeting_id,
        "method": result.method,
        "num_participants": len(result.participants),
        "participants": [_pi_to_dict(p) for p in result.by_rank()],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info("Influence JSON saved: %s", output_path)


def save_baselines_json(result: InfluenceResult, output_path: Path) -> None:
    """Write baseline scores to a separate JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "meeting_id": result.meeting_id,
        "baselines": [_baseline_to_dict(b) for b in result.baselines],
        "note": (
            "Baselines are stored separately from the proposed influence model. "
            "B1=speaking_time, B2=speaking_time+turns, "
            "B3=decision_event_count, B4=decision_evidence_count."
        ),
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info("Baselines JSON saved: %s", output_path)


def load_influence_json(path: Path) -> InfluenceResult:
    """Load an InfluenceResult from a saved JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Influence JSON not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    participants: list[ParticipantInfluence] = []
    for p in data.get("participants", []):
        dcs = [
            DecisionContribution(
                decision_id=dc["decision_id"],
                contribution_score=dc["contribution_score"],
                roles=dc["roles"],
                supporting_events=dc["supporting_events"],
            )
            for dc in p.get("decision_contributions", [])
        ]
        participants.append(ParticipantInfluence(
            participant=p["participant"],
            influence_score=p["influence_score"],
            rank=p["rank"],
            normalised_features=p.get("features", {}),
            raw_features=p.get("raw_features", {}),
            decision_contributions=dcs,
            supporting_decisions=p.get("supporting_decisions", []),
            supporting_events=p.get("supporting_events", []),
            explanation=p.get("explanation", []),
        ))

    return InfluenceResult(
        meeting_id=data["meeting_id"],
        method=data.get("method", {}),
        participants=participants,
        baselines=[],   # baselines are stored in a separate file
    )


# ---------------------------------------------------------------------------
# Top-level runner
# ---------------------------------------------------------------------------

def run_influence_analysis(
    events_path: Path,
    evidence_path: Path,
    decisions_path: Path,
    interactions_path: Path,
    meeting_id: str | None = None,
    output_dir: Path | None = None,
    ablation_flags: dict[str, bool] | None = None,
) -> tuple[InfluenceResult, Path, Path]:
    """
    Run Phase 11 participant influence analysis.

    Parameters
    ----------
    events_path       : Path to <meeting_id>_events.json
    evidence_path     : Path to <meeting_id>_evidence.json
    decisions_path    : Path to <meeting_id>_decisions.json
    interactions_path : Path to <meeting_id>_interactions.json
    meeting_id        : Override; derived from events file if None.
    output_dir        : Defaults to data/processed/influence/.
    ablation_flags    : {feature_key: bool} to disable features for ablation.

    Returns
    -------
    (InfluenceResult, influence_json_path, baselines_json_path)
    """
    t0 = time.time()

    for p in (events_path, evidence_path, decisions_path, interactions_path):
        if not p.exists():
            raise FileNotFoundError(f"Required input not found: {p}")

    event_result = load_events_json(events_path)
    evidence_result = load_evidence_json(evidence_path)
    decision_result = load_decisions_json(decisions_path)
    interaction_result = load_interactions_json(interactions_path)
    meeting_id = meeting_id or event_result.meeting_id

    num_dec_events = sum(
        1 for e in event_result.events
        if any(
            e.event_id in _decision_event_ids(d)
            for d in decision_result.decisions
        )
    )
    num_dec_evidence = sum(
        1 for r in evidence_result.relations
        if not r.source_event_id.startswith("slide:")
        and any(
            r.target_event_id in _decision_event_ids(d)
            for d in decision_result.decisions
        )
    )

    logger.info(
        "Influence analysis | meeting=%s | participants=%d | decisions=%d"
        " | decision_events=%d | decision_evidence=%d",
        meeting_id,
        len({e.speaker for e in event_result.events}),
        len(decision_result.decisions),
        num_dec_events,
        num_dec_evidence,
    )

    weights = _load_weights()
    result = compute_influence(
        event_result, evidence_result, decision_result, interaction_result,
        weights=weights, ablation_flags=ablation_flags,
    )

    elapsed = time.time() - t0

    logger.info(
        "Influence complete | participants=%d | top_speaker=%s | score=%.4f | %.2fs",
        len(result.participants),
        result.participants[0].participant if result.participants else "N/A",
        result.participants[0].influence_score if result.participants else 0.0,
        elapsed,
    )

    out_dir = output_dir or Path("data/processed/influence")
    out_dir.mkdir(parents=True, exist_ok=True)

    influence_path = out_dir / f"{meeting_id}_influence.json"
    baselines_path = out_dir / f"{meeting_id}_baselines.json"

    save_influence_json(result, influence_path)
    save_baselines_json(result, baselines_path)

    logger.info("Influence output  : %s", influence_path)
    logger.info("Baselines output  : %s", baselines_path)

    return result, influence_path, baselines_path
