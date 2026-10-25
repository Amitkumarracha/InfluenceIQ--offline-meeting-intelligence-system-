# Verified primary references for the new paper

Checked on 24 October 2026 against publisher/proceedings pages, official dataset/model documentation, and author institutional records. This is a focused reference catalog, not a systematic review. Include only works actually cited in the manuscript. The old professor-guidelines draft was inspected for useful sources, but its discussion-detector focus should not determine this manuscript's influence-centered claims.

## Important interpretation checks

- GAP: the 2018 publication describes 13 meetings; the evaluated ConvoKit release documents 28 meetings, 84 speakers, and 8,009 utterances. Cite both the paper and release documentation. AII is an outcome-alignment proxy; it cannot independently establish who caused a group decision.
- AMI: cite the 2006 publication for the corpus; the underlying conference was held in 2005. Reference-transcript experiments do not establish audio-to-influence accuracy.
- Influence/argumentation and evidence-grounded summaries have prior art. Do not claim the first influence detector, first meeting evidence links, or a novel sentence encoder.
- Keep published work in related work; the local measurements are not comparable without matched data, labels, splits, and metrics.
- The AI annotation pilot is assistant-labelled material. These references do not turn it into human ground truth or validated causal attribution.
- Pages for Rienks et al. 2007 were omitted because the institutional record and a bibliographic index disagree. DOI, title, authors, and venue identify the work without asserting an unresolved page range.
- No DOI is supplied for Fernández et al. 2008 or Kirstein et al. 2025 because their checked ACL records do not list one.

## Citation catalog

### `rienks2007`

R. J. Rienks, A. Nijholt, and D. K. J. Heylen, “Verbal behavior of the more and the less influential meeting participant,” in Proceedings of the Workshop on Tagging, Mining and Retrieval of Human Related Activity Information, 2007. doi: 10.1145/1330588.1330589.

**Primary verification:** [Proceedings of the Workshop on Tagging, Mining and Retrieval of Human Related Activity Information](https://research.utwente.nl/en/publications/verbal-behavior-of-the-more-and-the-less-influential-meeting-part/).

**Use:** Prior work links argumentation and dialogue behavior with influence perceived by AMI participants. Establishes prior art; no numerical comparison with our outcome-alignment target.

**Verification note:** Institutional primary record lists pages 2–9; another index lists 1–8. Page range omitted pending publisher reconciliation.

### `mayfield2019`

E. Mayfield, and A. Black, “Stance Classification, Outcome Prediction, and Impact Assessment: NLP Tasks for Studying Group Decision-Making,” in Proceedings of the Third Workshop on Natural Language Processing and Computational Social Science, pp. 65–77, 2019. doi: 10.18653/v1/W19-2108.

**Primary verification:** [Proceedings of the Third Workshop on Natural Language Processing and Computational Social Science](https://aclanthology.org/W19-2108/).

**Use:** Defines stance, outcomes, and impact tasks in Wikipedia discussions. Supports separating these constructs; not a spoken-meeting or matched ranking benchmark.

### `gap2018`

M. Braley, and G. Murray, “The Group Affect and Performance (GAP) Corpus,” in Proceedings of the Group Interaction Frontiers in Technology, Article 2, 9 pages, 2018. doi: 10.1145/3279981.3279985.

**Primary verification:** [Proceedings of the Group Interaction Frontiers in Technology](https://doi.org/10.1145/3279981.3279985).

**Use:** Original GAP corpus paper, with individual and group Winter Survival rankings and influence measure. Original publication describes thirteen meetings; cite current release separately for twenty-eight.

**Additional primary source:** https://convokit.cornell.edu/documentation/gap.html

**Verification note:** Author manuscript indexed at UFV and citation metadata on official ConvoKit page were checked. Direct author-PDF link currently returns 404 and ACM endpoint denies automated access. DOI corroborated by bibliographic records; no publisher page range asserted.

### `gaprelease`

Cornell Conversational Analysis Toolkit, “Group Affect and Performance (GAP) Corpus,” ConvoKit dataset documentation. Accessed: Oct. 24, 2026. [Online]. Available: https://convokit.cornell.edu/documentation/gap.html

**Primary verification:** [ConvoKit dataset documentation](https://convokit.cornell.edu/documentation/gap.html).

**Use:** Official evaluated-release documentation reports 28 English conversations, 84 speakers, 8,009 utterances and decision-process metadata. This is release documentation, not an additional peer-reviewed study.

### `ami2006`

J. Carletta et al., “The AMI Meeting Corpus: A Pre-announcement,” in Machine Learning for Multimodal Interaction, vol. 3869, pp. 28–39, 2006. doi: 10.1007/11677482_3.

**Primary verification:** [Machine Learning for Multimodal Interaction](https://research.utwente.nl/en/publications/the-ami-meeting-corpus-a-pre-announcement/).

**Use:** Credits AMI as pre-existing multimodal meeting corpus. Publication year 2006 refers to LNCS proceedings of MLMI 2005.

**Additional primary source:** https://groups.inf.ed.ac.uk/ami/corpus/overview.shtml

### `calo2010`

G. Tur et al., “The CALO Meeting Assistant System,” IEEE Transactions on Audio, Speech, and Language Processing, vol. 18, no. 6, pp. 1601–1611, 2010. doi: 10.1109/TASL.2009.2038810.

**Primary verification:** [IEEE Transactions on Audio, Speech, and Language Processing](https://www.microsoft.com/en-us/research/publication/the-calo-meeting-assistant-system/).

**Use:** Prior integrated meeting architecture includes transcription, dialogue analysis, decision extraction and summarization. Local deployment and component integration alone are not novel.

### `fernandez2008`

R. Fernández, M. Frampton, P. Ehlen, M. Purver, and S. Peters, “Modelling and Detecting Decisions in Multi-party Dialogue,” in Proceedings of the 9th SIGdial Workshop on Discourse and Dialogue, pp. 156–163, 2008. [Online]. Available: https://aclanthology.org/W08-0125/

**Primary verification:** [Proceedings of the 9th SIGdial Workshop on Discourse and Dialogue](https://aclanthology.org/W08-0125/).

**Use:** Prior multi-party decision modeling and detection; supports treating decision emergence as a discourse task rather than counting generic agreement.

**Verification note:** ACL record provides no DOI; none invented.

### `explainmeetsum2023`

H. Kim, M. Cho, and S.-H. Na, “ExplainMeetSum: A Dataset for Explainable Meeting Summarization Aligned with Human Intent,” in Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers), pp. 13079–13098, 2023. doi: 10.18653/v1/2023.acl-long.731.

**Primary verification:** [Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)](https://aclanthology.org/2023.acl-long.731/).

**Use:** Human-annotated evidence-to-summary alignment demonstrates prior evidence-grounding work in meetings. Evidence extraction differs from participant influence.

### `qmsum2021`

M. Zhong et al., “QMSum: A New Benchmark for Query-based Multi-domain Meeting Summarization,” in Proceedings of the 2021 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies, pp. 5905–5921, 2021. doi: 10.18653/v1/2021.naacl-main.472.

**Primary verification:** [Proceedings of the 2021 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies](https://aclanthology.org/2021.naacl-main.472/).

**Use:** Query-focused meeting span selection and summarization are established tasks, distinct from source-linked participant contribution ranking.

### `meetingbank2023`

Y. Hu, T. Ganter, H. Deilamsalehy, F. Dernoncourt, H. Foroosh, and F. Liu, “MeetingBank: A Benchmark Dataset for Meeting Summarization,” in Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers), pp. 16409–16423, 2023. doi: 10.18653/v1/2023.acl-long.906.

**Primary verification:** [Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)](https://aclanthology.org/2023.acl-long.906/).

**Use:** City-council meeting corpus aligns professional minutes with transcript segments; a neighboring task and potential future domain, not an evaluated dataset here.

### `whisper2023`

A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey, and I. Sutskever, “Robust Speech Recognition via Large-Scale Weak Supervision,” in Proceedings of the 40th International Conference on Machine Learning, vol. 202, pp. 28492–28518, 2023. [Online]. Available: https://proceedings.mlr.press/v202/radford23a.html

**Primary verification:** [Proceedings of the 40th International Conference on Machine Learning](https://proceedings.mlr.press/v202/radford23a.html).

**Use:** Credits pretrained Whisper ASR. Published model performance is not project-specific audio or influence accuracy.

### `pyannote2023`

H. Bredin, “pyannote.audio 2.1 speaker diarization pipeline: principle, benchmark, and recipe,” in Proceedings of Interspeech 2023, pp. 1983–1987, 2023. doi: 10.21437/Interspeech.2023-105.

**Primary verification:** [Proceedings of Interspeech 2023](https://www.isca-archive.org/interspeech_2023/bredin23_interspeech.html).

**Use:** Credits a speaker-diarization architecture if the manuscript discusses this backend; do not imply current GAP reference-speaker evaluation used automatic diarization.

### `sbert2019`

N. Reimers, and I. Gurevych, “Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks,” in Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing and the 9th International Joint Conference on Natural Language Processing, pp. 3982–3992, 2019. doi: 10.18653/v1/D19-1410.

**Primary verification:** [Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing and the 9th International Joint Conference on Natural Language Processing](https://aclanthology.org/D19-1410/).

**Use:** Credits sentence-transformer embeddings and cosine similarity, not a newly proposed project encoder.

### `minilm2020`

W. Wang, F. Wei, L. Dong, H. Bao, N. Yang, and M. Zhou, “MiniLM: Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Transformers,” in Advances in Neural Information Processing Systems, vol. 33, 2020. [Online]. Available: https://proceedings.neurips.cc/paper/2020/hash/3f5ee243547dee91fbd053c1c4a845aa-Abstract.html

**Primary verification:** [Advances in Neural Information Processing Systems](https://proceedings.neurips.cc/paper/2020/hash/3f5ee243547dee91fbd053c1c4a845aa-Abstract.html).

**Use:** Credits MiniLM base architecture/distillation. The exact all-MiniLM-L6-v2 sentence checkpoint requires its own model-card citation.

### `minilmcheckpoint`

Sentence Transformers, “all-MiniLM-L6-v2,” Model card. Accessed: Oct. 24, 2026. [Online]. Available: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2

**Primary verification:** [Model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).

**Use:** Documents actual 384-dimensional sentence encoder and its contrastive training. Separate frozen embedding extraction from project contextual fine-tuning experiments.

### `rf2001`

L. Breiman, “Random Forests,” Machine Learning, vol. 45, no. 1, pp. 5–32, 2001. doi: 10.1023/A:1010933404324.

**Primary verification:** [Machine Learning](https://link.springer.com/article/10.1023/A:1010933404324).

**Use:** Credits the random forest supporting discussion classifier; does not explain the separate weighted influence score.

**Additional primary source:** https://www.stat.berkeley.edu/~breiman/randomforest2001.pdf

### `extratrees2006`

P. Geurts, D. Ernst, and L. Wehenkel, “Extremely randomized trees,” Machine Learning, vol. 63, pp. 3–42, 2006. doi: 10.1007/s10994-006-6226-1.

**Primary verification:** [Machine Learning](https://doi.org/10.1007/s10994-006-6226-1).

**Use:** Credits the Extra Trees regression estimator selected in the initial GAP experiment.

### `xgboost2016`

T. Chen, and C. Guestrin, “XGBoost: A Scalable Tree Boosting System,” in Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, pp. 785–794, 2016. doi: 10.1145/2939672.2939785.

**Primary verification:** [Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining](https://doi.org/10.1145/2939672.2939785).

**Use:** Credits later exploratory gradient-boosted tree experiment; higher development score did not establish held-out improvement.

### `sklearn2011`

F. Pedregosa et al., “Scikit-learn: Machine Learning in Python,” Journal of Machine Learning Research, vol. 12, pp. 2825–2830, 2011. [Online]. Available: https://www.jmlr.org/papers/v12/pedregosa11a.html

**Primary verification:** [Journal of Machine Learning Research](https://www.jmlr.org/papers/v12/pedregosa11a.html).

**Use:** Credits ML implementations and preprocessing; publisher author list differs from later expanded arXiv version.

### `cawley2010`

G. C. Cawley, and N. L. C. Talbot, “On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation,” Journal of Machine Learning Research, vol. 11, pp. 2079–2107, 2010. [Online]. Available: https://jmlr.org/papers/v11/cawley10a.html

**Primary verification:** [Journal of Machine Learning Research](https://jmlr.org/papers/v11/cawley10a.html).

**Use:** Supports transparent development selection and caution with repeated inspection/model search. Does not repair historical-cohort reuse.

### `dror2018`

R. Dror, G. Baumer, S. Shlomov, and R. Reichart, “The Hitchhiker's Guide to Testing Statistical Significance in Natural Language Processing,” in Proceedings of the 56th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers), pp. 1383–1392, 2018. doi: 10.18653/v1/P18-1128.

**Primary verification:** [Proceedings of the 56th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)](https://aclanthology.org/P18-1128/).

**Use:** Supports matching uncertainty analysis to the evaluation design. Our few-group bootstrap intervals are descriptive; no significance is inferred.

### `she2024`

S. She, S. Huang, X. Wang, Y. Zhou, and J. Chen, “Exploring the Factual Consistency in Dialogue Comprehension of Large Language Models,” in Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers), pp. 6087–6100, 2024. doi: 10.18653/v1/2024.naacl-long.338.

**Primary verification:** [Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)](https://aclanthology.org/2024.naacl-long.338/).

**Use:** Recent primary work examines dialogue subject/object comprehension and factuality. Neighboring motivation only, not evidence of errors or benefits of this system.

### `kirstein2025`

F. Kirstein, T. Ruas, and B. Gipp, “What's Wrong? Refining Meeting Summaries with LLM Feedback,” in Proceedings of the 31st International Conference on Computational Linguistics, pp. 2100–2120, 2025. [Online]. Available: https://aclanthology.org/2025.coling-main.143/

**Primary verification:** [Proceedings of the 31st International Conference on Computational Linguistics](https://aclanthology.org/2025.coling-main.143/).

**Use:** Recent meeting-specific error-analysis study introduces human-annotated generated-summary errors. Supports semantic review and distinguishes independent annotation from single-assistant labels.

**Verification note:** ACL record does not list a DOI; none invented.

### `wright2025`

D. Wright, Z. M. Mujahid, L. Wang, I. Augenstein, and D. Jurgens, “Unstructured Evidence Attribution for Long Context Query Focused Summarization,” in Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing, pp. 1839–1867, 2025. doi: 10.18653/v1/2025.emnlp-main.95.

**Primary verification:** [Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing](https://aclanthology.org/2025.emnlp-main.95/).

**Use:** Recent source-evidence attribution work; demonstrates that citation extraction is an evaluated task in its own right. General long-context summarization, not participant influence.

