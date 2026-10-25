# GAP outcome-influence experiment — 24 October 2026

The development-selected model did not beat the word-count baseline on the final test groups. It was not installed in the app. This is a real external-corpus pilot, not a 75%+ application-accuracy claim.

## Data and task

The [GAP corpus](https://convokit.cornell.edu/documentation/gap.html) contains 28 meetings, 84 participants and 8,009 utterances. Its Absolute Individual Influence (AII) is a distance between a participant's individual pre-meeting item ranking and the final group ranking; lower AII means greater outcome alignment. This is a proxy for outcome influence, not causal influence or independent judgments of presenter impact. The source is [Braley and Murray, 2018](https://doi.org/10.1145/3279981.3279985); the downloadable release is licensed CC BY-NC 4.0.

Training uses 16 complete groups/45 participants; development uses six groups/20 participants; testing uses six groups/19 participants. The group split uses seed 20261024 and is frozen in the protocol before fitting. Reference English transcripts and speaker IDs are supplied: no ASR, slides, Hindi/Hinglish or deployment accuracy is established.

## Model selection

Thirty learned configurations compare ridge regression, a pairwise logistic ranker and Extra Trees, each using structure features, word/bigram TF-IDF or their combination. Five simple baselines are also eligible for primary selection. Structure features include observed timing, word/utterance counts, lexical markers, automatically extracted event counts and the existing seven influence features. TF-IDF and standardization fit training data only. No demographics, questionnaires, expert/group ranking scores, manual decision tags or sentiment annotations enter features. AII enters only the training target and evaluation reference.

Each model family/feature combination retains its development-selected parameter. The primary method is selected across all 35 candidates by development meeting-average pairwise accuracy; ties use the fixed candidate order. Training and final evaluation run as separate commands. Model, data, feature-source and configuration hashes are checked before final scoring.

The selected primary is **structure__extra_trees**, with minimum leaf size 5 and 150 trees. Development pairwise accuracy is **83.33%**, versus **82.78%** for word count. These development figures must not be presented as test results.

## Frozen final results

Pairwise accuracy excludes reference ties, gives predicted ties half credit and weights each meeting equally. Top-set accuracy requires the complete predicted top set to equal the reference top set. It is a separate, more demanding metric. All-human-tied groups would be unavailable for ordering accuracy.

| Frozen method | Test pairwise accuracy | Test exact top-set accuracy |
| --- | ---: | ---: |
| speaking_time | 52.78% | 33.33% |
| word_count | 63.89% | 50.00% |
| utterance_count | 41.67% | 33.33% |
| decision_count | 52.78% | 16.67% |
| prototype_influence | 52.78% | 16.67% |
| structure__ridge | 55.56% | 16.67% |
| structure__pairwise_logistic | 47.22% | 16.67% |
| structure__extra_trees **(primary selected on development)** | 61.11% | 33.33% |
| text__ridge | 41.67% | 16.67% |
| text__pairwise_logistic | 47.22% | 16.67% |
| text__extra_trees | 58.33% | 50.00% |
| combined__ridge | 55.56% | 16.67% |
| combined__pairwise_logistic | 47.22% | 16.67% |
| combined__extra_trees | 66.67% | 50.00% |

The primary scores **61.11%**, below the word-count baseline's **63.89%**. Its meeting-bootstrap 95% interval is **33.33%–83.33%**, based on 10,000 resamples of only six test groups. This small sample supports no superiority or significance claim. The combined-feature Extra Trees model scores 66.67%, but it was not the development-selected primary; replacing the primary with it after seeing test results would be test-based model selection.

## What the experiment tells us

The existing prototype score reaches 52.78% on this task. Several learned candidates improve that point estimate, but the declared primary does not beat a trivial word-count ranking. A larger development score did not establish better generalization. Aggregate contribution counts and lexical features have not demonstrated the outcome-influence representation needed for a strong paper. The experiment does not prove that more data or a larger model will solve this; those remain hypotheses.

The next experiments should measure proposal-to-outcome links and cross-speaker uptake on training/development data, then compare trained relationship features against the same baselines. Independently annotated presenter meetings are needed to validate the intended construct, with more independent groups and verified speakers. Existing test groups must be treated as historical after any test-informed development; preserve these results and reserve fresh groups for confirmation.

## Artifacts and reproduction

- [Protocol](../../outputs/training/gap_influence_20261024/protocol.json): group IDs, feature definitions, candidate grid, source/data hashes and target meaning.
- [All development trials](../../outputs/training/gap_influence_20261024/development_search.json).
- [Frozen selection](../../outputs/training/gap_influence_20261024/selection.json).
- [Final per-meeting results and predictions](../../outputs/training/gap_influence_20261024/test_results.json).

The links above are local research artifacts; outputs and downloaded data remain excluded from Git. Downloaded JSON data and its source archive are under `.runtime/research-influence-gap/`. The source archive SHA-256 is `bdb2ef3310f44bfc96c7929de99d610b6de0c984db6c52cee7206e55772314fd`. Each selected input file has its own digest in the protocol.

Later attribution corrections changed the active production sources. The exact
sources for this experiment are preserved under the artifact directory's
`source_snapshot/`, verified against the original hashes. Restore that snapshot
into an isolated checkout before reproducing these particular results. A run
against current app sources evaluates a different pipeline version.

From the repository root, with the archive's `speakers.json`, `conversations.json` and `utterances.jsonl` extracted into the isolated data directory:

```bash
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv/bin/python scripts/benchmark_gap_influence.py \
  --data .runtime/research-influence-gap \
  --output-dir outputs/training/gap_influence_reproduction
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv/bin/python scripts/benchmark_gap_influence.py \
  --data .runtime/research-influence-gap \
  --output-dir outputs/training/gap_influence_reproduction --evaluate
```

Training requires a fresh output directory. Final evaluation refuses to overwrite an existing test-results file. A reproduction is not a fresh independent test. The script saves research models separately and never changes application settings or installs a model.
