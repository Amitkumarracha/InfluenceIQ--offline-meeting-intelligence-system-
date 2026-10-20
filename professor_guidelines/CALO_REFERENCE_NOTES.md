# Reading the professor's CALO reference

The supplied PDF is Gokhan Tur et al., *The CALO Meeting Assistant System*, IEEE Transactions on Audio, Speech, and Language Processing, 18(6), 2010. DOI: https://doi.org/10.1109/TASL.2009.2038810.

The paper describes capture, transcription and semantic analysis of multiparty meetings. Its architecture supports both live and offline processing and analyses dialogue structure, topics, questions/answers, action items and decisions. Its discussion of decisions treats them as conversational structures across multiple utterances rather than isolated keywords. This is particularly relevant to InfluenceIQ's evidence and decision-chain design.

InfluenceIQ does not reproduce CALO's trained classifiers or its reported evaluation. The current project uses pretrained local speech components and transparent NLP rules with reviewable evidence. It deliberately omits generative summaries and question answering. Its contribution should be described as a local deployment and evidence-review integration, with a modest calibration experiment. Neither offline execution nor action-item extraction alone establishes novelty because prior systems already discuss such capabilities.

Useful lessons for the report:

1. Separate capture, recognition and semantic interpretation, and evaluate their errors separately.
2. Treat a decision as a sequence that can include proposals, objections and revisions. Do not treat every future-tense sentence as a final decision.
3. Show exactly what evidence supports a candidate and let users correct it.
4. Do not compare our pilot WER/DER directly with CALO's published numbers: corpora, microphones, splits, models and protocols differ.
5. State limitations of multilingual rules, name inference and participant attribution. CALO's historical results are related work, not measurements of this project.

Read the full supplied PDF alongside the manuscript. No figures or tables from it have been copied into the new paper; the diagrams in this folder are original descriptions of the present implementation.

## How its writing structure informs this manuscript

CALO is used as an example of technical exposition, not a template to copy. The revised manuscript introduces the problem and scope, compares related work, explains the complete architecture, defines component interfaces and scoring, declares an evaluation protocol, and then separates results from interpretation. Each figure has a short caption and an explicit reference in the prose. New diagrams describe InfluenceIQ only. Unlike the historical reference, our current evidence is a small exploratory pilot, which must remain explicit in the abstract and conclusions.
