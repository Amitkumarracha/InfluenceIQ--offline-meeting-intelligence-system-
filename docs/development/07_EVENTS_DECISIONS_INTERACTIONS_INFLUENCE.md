# Events, evidence, decisions, interactions, and influence

Layout update, 8 October 2026: use the [master documentation](../README.md) and [structure/performance update](../validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md). Historical comparisons and measurements below describe their stated audit date. The older working tree is now archived; current paths and runtime are described in the update.

[Handbook index](../handbook/README.md)

## Event extraction

[`events.py`](../../src/meeting/events.py) defines 11 configured types: proposal, question, objection, evidence, correction, clarification, agreement, disagreement, revision, decision, and action_item.

`KeywordEventExtractor` receives transcript or multimodal segment dictionaries. It keeps original text, speaker and timestamps, selected slide, and source segment ID. It selects the highest-scoring matching type per segment, skips nonmatching segments, and applies the configured confidence threshold 0.3. It is not multi-label dialogue-act classification.

English score is `min(1, 3 * hits / number_of_patterns_for_type)`. Separate bilingual score is `min(0.8, 0.6 * bilingual_hits)`; the type score is the maximum of the English and bilingual values. Blocker matches suppress that type. The score measures phrase-match density, not calibrated semantic correctness.

The current version adds Hindi/Hinglish expressions, commitments such as “I'll send…”, Unicode NFKC/casefold normalization, curly-apostrophe normalization, and question/negation guards in [`language_rules.py`](../../src/meeting/language_rules.py). Separate banks avoid diluting English scores merely by adding another language's patterns. Context, sarcasm, coreference, topic switching, implicit agreement, and uncommon phrasing remain difficult.

Android exports and reuses phrase/blocker banks but emits every type with a surviving pattern match. It does not apply the laptop's highest-score selection/threshold rule. Shared banks therefore do not imply identical event predictions across devices.

## Evidence links

[`evidence.py`](../../src/meeting/evidence.py) is byte-identical to the older copy. Events are sorted by start time; the most recent suitable preceding event within 60 seconds is selected.

| Source | Allowed target | Relation |
| --- | --- | --- |
| Slide associated with an event | That event | `supports` with source `slide:<slide_id>` |
| Objection/disagreement | Proposal/decision/revision | `contradicts` |
| Agreement | Proposal/decision/revision | `supports` |
| Revision | Proposal | `modifies` |
| Correction | Prior configured event | `modifies` |
| Clarification | Prior configured event | `clarifies` |
| Evidence event | Prior configured event | `supports` |

The relationship vocabulary also includes `affects` and `references`, but a listed vocabulary entry does not mean every relation is inferred by these rules.

A slide association becomes a supports edge by heuristic convention. It does not test factual support. Temporal proximity can link unrelated topics or speakers; these edges require independent human validation. Every edge retains source/target event IDs and optional slide information for traceability.

## Decision reconstruction

[`decisions.py`](../../src/meeting/decisions.py) is mostly inherited. It anchors explicit decision events, and optionally agreements when any earlier proposal exists. Anchors within approximately half the 120-second window are deduplicated. If there are no anchors, proposals become fallback anchors. Events overlapping `[anchor.start - 120, anchor.end + 120]` form a cluster; already-used events are assigned to the earliest cluster.

The first proposal is the representative proposal, the last explicit decision becomes final decision, and discussion/evidence/revisions/agreements and source IDs are retained. The topic is a simple text-derived label, not learned topic modeling. Roles include proposer, objector, evidence provider, reviser, supporter, and final decision maker.

| Status | Executable rule |
| --- | --- |
| `confirmed` | Cluster has an explicit decision-type event |
| `probable` | No explicit final decision, but an agreement exists |
| `conflicting` | Multiple proposals and objection without agreement |
| `unresolved` | Otherwise |

These are system labels, not adjudicated meeting outcomes. Decision confidence is left `None`. The agreement anchor's preceding-proposal test is not topic-aware. An explicit decision phrase can be misclassified by the event stage.

**Confirmed audit issue:** `require_final_decision=True` suppresses agreement anchors but does not suppress proposal fallback when no decision anchors exist. A one-proposal fixture still yields an unresolved decision with no final decision. The handbook documents actual behavior; no code was changed during this audit.

Decision lineage joins events with proposal/revision/agreement/final-decision and evidence-derived edges. Graph JSON now serializes source node/edge lists directly, preserving listed parallel relationships; optional NetworkX helpers remain. A graph expresses inferred discussion structure, not causality.

## Interaction analysis

[`interaction.py`](../../src/meeting/interaction.py) uses three passes: evidence relations → interactions, decision-lineage edges → interactions, and reactive-event types → preceding targetable events within a 60-second window. IDs/source types support deduplication and traceability. Participant statistics describe initiated/received interactions and type counts.

Graph edges represent speaker-to-speaker inferred interaction records. Current JSON serialization writes each record directly instead of constructing a graph just to export it. The optional participant graph helper uses `MultiDiGraph`. No conversational response model, semantic pass, or learned graph network is present; `interaction.semantic_threshold` is a reserved value.

UNKNOWN labels may still appear in event, decision, or interaction structures. The main workflow with unavailable diarization explicitly withholds participant influence rather than treating UNKNOWN as a real person.

## Influence formula

[`influence.py`](../../src/meeting/influence.py) computes a **decision-linked weighted feature score** in both versions. The older README's “PageRank-style” claim does not match executable scoring: no PageRank calculation is used for influence.

For participant `p`, raw feature `x(p,k)`, and each feature `k`:

```text
z(p,k) = x(p,k) / max_q x(q,k)    if that maximum > 0; otherwise 0
I(p) = sum_k w(k) * z(p,k)
```

Configured weights are clipped to nonnegative values and normalized to sum to one. Default YAML weights already sum to one.

| Feature / weight | Raw contribution rule |
| --- | --- |
| Proposal / 0.15 | +1 for proposal in a decision cluster; another +1 for a confirmed cluster with final decision |
| Evidence / 0.20 | +1 for decision-linked evidence event; +0.5 if slide-grounded |
| Objection / 0.15 | +0.5 for decision-linked objection/disagreement; +1 if a later revision exists in that cluster |
| Revision / 0.20 | +1 for revision in a confirmed/probable cluster |
| Decision / 0.15 | +1 per cluster event in confirmed decisions; +0.5 in probable decisions |
| Interaction / 0.05 | +1 per initiated interaction associated with a decision |
| Slide grounding / 0.10 | +1 per decision-linked event associated with a slide |

Scores are rounded and ranked descending with shared ranks for ties. UNKNOWN is excluded. Participants without extracted events can have speaking statistics but no influence vector. Without valid speaker separation, the complete pipeline marks influence `unavailable_without_diarization`.

“Objection followed by revision” is temporal association, not proof that the objection caused revision. The model mixes several overlapping signals: slide-grounded evidence receives both an evidence bonus and a grounding feature, and decision events can also count as proposal/interaction contributions. Weights are prototype choices, not learned or tuned results.

Per-decision contribution is a proxy: speaker fraction of cluster events multiplied by the average of that speaker's meeting-level normalized features. It is not a separately normalized causal contribution measure.

## Speaking-time baselines and important distinction

Main `run_influence_analysis()` now reloads the full transcript when available to compute B1 speaking time and B2 speaking time/segment-count baselines. Report participant statistics also use the full transcript. “Turn count” here counts transcript segments, which is not necessarily conversational turn segmentation.

However, `src/evaluation/baselines.py` and A8 still operate on extracted events, not the full transcript. Some baseline functions also retain UNKNOWN. Evaluation CLI values must not be silently equated with corrected main-runner baselines. See [11](../research/11_EVALUATION_BASELINES_AND_ABLATIONS.md).

## Traceability chain

```text
Audio time interval → transcript segment ID → event ID
    → optional selected slide and evidence relation ID
    → decision ID and lineage edges
    → interaction ID → raw/normalized influence features
```

The chain is a useful research design: it lets humans inspect why a score or decision candidate was emitted. Traceability validates that a source link exists; it does not establish that every inferred relation is true.
