# Exact fusion methods implemented

Layout update, 8 October 2026: use the [master documentation](../README.md) and [structure/performance update](../validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md). Historical comparisons and measurements below describe their stated audit date. The older working tree is now archived; current paths and runtime are described in the update.

[Handbook index](../handbook/README.md)

## What is fused

The laptop fuses **ASR transcript text/timestamps/speaker metadata** with **textual information extracted from presentation slides**. Acoustic input reaches fusion through ASR; images contribute structural metadata but no learned visual embeddings. The implementation is a modular score-level alignment and a joined multimodal record.

There is no trained audio-image cross-attention network, joint acoustic/visual encoder, tensor/bilinear fusion, learned gating, video/face fusion, or newly trained multimodal model. Android has no slide fusion. Multiple uploaded audio parts are sequential inputs, not independent modalities.

The temporal/semantic components and weighted combination already existed in the supplied older copy. The current extension is an optional lexical TF-IDF content score and recorded method metadata.

## Slide representation

[`build_slide_text()`](../../src/ppt/embeddings.py) concatenates title → body text → table cell text → notes. Native PPTX extraction is implemented; OCR is a stub whose availability function always returns false. Setting an OCR-looking flag does not make OCR work.

Default model: `all-MiniLM-L6-v2`. A slide embedding matrix has one row per slide; the model produces 384-dimensional embeddings. This dimensionality is documented in its [upstream model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2). No Hindi/English cross-language alignment result is available for this local project.

## Temporal score

For transcript segment `i = [a_i,b_i]` and a slide with display interval `j = [s_j,e_j]`:

```text
overlap(i,j) = max(0, min(b_i,e_j) - max(a_i,s_j))
T(i,j) = min(1, overlap(i,j) / max(b_i-a_i, 1e-9))
```

[`temporal_alignment.py`](../../src/fusion/temporal_alignment.py) returns `None` when either slide timestamp is missing. It never invents display times from slide order. A normal uploaded PPTX does not establish when its slides were shown; the main PPT extraction path does not infer those intervals.

If any slide has valid timing and there are positive-overlap slides, candidates are limited to those slides. If none overlap, all slides remain candidates. If no timings exist, all slides remain candidates. Although an older comment mentions a safety margin, the executable candidate filter does not add an explicit margin.

This hard prefilter can exclude semantically related offscreen slides whenever another slide overlaps. Mixed timed/untimed slide sets also need evaluation: untimed slides can be excluded when timed slides overlap.

## Default semantic score

[`semantic_alignment.py`](../../src/fusion/semantic_alignment.py) embeds segment text with the same model and computes cosine similarity:

```text
S(i,j) = dot(u_i, v_j) / (norm(u_i) * norm(v_j))
```

Vectors are L2-normalized with epsilon protection. Raw cosine scores can be negative; they are not calibrated probabilities. Empty segment text gets a zero vector. This is text relevance matching, not semantic entailment or a proof that a slide supports the spoken claim.

## Optional lexical score

With `alignment.method: tfidf`, [`lexical_alignment.py`](../../src/fusion/lexical_alignment.py) builds a sparse index over slide texts:

```text
idf(t) = 1 + ln((1 + number_of_slides) / (1 + slide_document_frequency(t)))
tf(t,d) = 1 + ln(count(t,d))
w(t,d) = tf(t,d) * idf(t), then L2-normalize
L(i,j) = dot(normalized_query_vector, normalized_slide_vector)
```

Terms absent from the slide vocabulary are ignored. Unicode letter/number/combining-mark tokenization preserves Hindi spellings. A postings index accumulates nonzero overlaps; output scores are clamped to [0,1]. No neural embedding model is loaded for this path.

TF-IDF **replaces** the semantic content scorer in a run; embeddings and TF-IDF are not jointly ensembled. Both methods still share temporal filtering and weighted combination. Internally, the JSON field named `semantic_score` carries lexical relevance for TF-IDF runs; inspect `alignment_method` before interpreting it.

TF-IDF misses paraphrases, synonyms, transliterations, and cross-script matches unless terms actually overlap. Lower runtime/dependency cost is a hypothesis to measure under matched experiments, not evidence of universally better alignment.

## Score combination and abstention

[`combine_scores()` / `align_segment()`](../../src/fusion/multimodal_representation.py):

```text
C(i,j) = (w_t*T(i,j) + w_s*S(i,j)) / (w_t+w_s), when timing exists
C(i,j) = S(i,j), when timing is absent and w_s > 0
```

Use `L` instead of `S` for the TF-IDF option. Zero total weight with available timing gives 0. In the current missing-timing branch, `semantic_weight=0` gives 0 as well; do not assume the docstring's semantic-only fallback applies regardless of weights.

Current defaults: `w_t=0.5`, `w_s=0.5`, `top_k=3`, threshold `0.3`. Rank candidates descending, retain top-k, and select the best only if `combined_score >= threshold`; otherwise emit `NO_CONFIDENT_SLIDE`. Heuristic labels are high at threshold+0.15, medium at threshold, otherwise low. They are not statistical confidence estimates.

Without slide timings, the default 0.5/0.5 weights effectively yield semantic-only alignment. A paper must report the fraction of evaluated slides with real timings; it cannot claim a temporal-fusion benefit solely because the YAML contains temporal weights.

## Unified representation and downstream use

`MultimodalSegment` stores segment ID, speaker, absolute start/end, original text, selected slide/sentinel, and temporal/content/combined scores. Candidate-level output retains top-k slide candidates and individual scores.

Event extraction carries the selected slide ID into an event. Evidence extraction adds a heuristic `slide:<id> → event` supports edge. Decisions collect source segments, slides, roles, and lineage. Influence uses slide-grounded decision-linked event counts and a slide bonus on evidence events. This is downstream use of grounding metadata, not a jointly learned multimodal reasoning system.

For a paper, a precise description is: **“A modular transcript–slide alignment pipeline combines text-content similarity with optional display-time overlap, permits threshold-based abstention, and propagates source identifiers into heuristic decision lineage and contribution scoring.”**

## Fusion experiments still needed

Compare semantic-only, temporal-only on genuinely timed slides, combined timing+semantic, TF-IDF-only, timing+TF-IDF, and no-PPT. Run the relevant alignment stage again for each method on identical held-out inputs. Annotate slide relevance independently, include legitimate no-slide cases, and report top-1 accuracy, top-k recall, abstention precision/coverage, and resource use.

The inherited A3/A4 influence-weight ablations do not perform these fusion removals. See [11](11_EVALUATION_BASELINES_AND_ABLATIONS.md).
