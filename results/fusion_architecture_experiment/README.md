# Early, intermediate and late fusion: prototype outputs

NEW CONSTRUCTED-CASE PROTOTYPE EXPERIMENT — NOT DEPLOYED-SYSTEM ACCURACY

Derived transcript/document text embeddings plus timing, not raw acoustic/image fusion. No real meeting labels.

These are actual newly computed predictions, not invented showcase values. They use the existing constructed cases, not independently labelled real meetings.

| Prototype | Correct / total | Top-1 | Grounded F1 |
| --- | ---: | ---: | ---: |
| early | 7/24 | 29.17% | 33.33% |
| intermediate | 9/24 | 37.50% | 40.00% |
| late | 14/24 | 58.33% | 66.67% |

## Implementations

- **early:** Concatenate frozen passage/slide embeddings and timing cues, then train a 32-unit MLP.
- **intermediate:** Train separate 16-unit passage/slide projections; fuse representations, differences/products and timing cues in a prediction head.
- **late:** Fit separate semantic-cosine and timing logistic experts; average probabilities when timing exists, otherwise use semantic probability.

## Limitations

- Only 24 previously examined author-designed cases; 13 unique passage texts and one fixed six-slide catalog.
- No independent real-meeting or unseen-slide evaluation; no ASR or raw image/acoustic features.
- One seed, fixed hyperparameters/threshold, different architecture sizes; not an optimized or capacity-matched benchmark.
- Late experts receive engineered similarity/timing cues; neural prototypes receive embeddings/timing.
- Exploratory prototypes are not installed in the application and do not establish a general winner.

Regenerate: `.venv/bin/python scripts/compare_fusion_architectures.py`. Inspect `predictions.csv`, `comparison.csv` and `results.json`. Original saved application evaluations are unchanged.
