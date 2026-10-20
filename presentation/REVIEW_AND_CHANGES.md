# Review and changes — final 18-slide MAI deck

The final deck follows the original PPT's **18 headings in their original order**. The cover matches the supplied reference layout, corrected to **MAI Project AY 2026–27**. The original rough file is unchanged.

| Slide | Retained heading | Final content |
| --- | --- | --- |
| 1 | MAI Project AY 2026–27 | Reference-style cover: ESE presentation, project ID/title, institutional logo, faculty guide and numbered team members. |
| 2 | Introduction | The everyday recording-review problem. |
| 3 | Problem Statement | Illustrative dialogue distinguishes relevant discussion from an accepted decision. |
| 4 | Objectives of the Project | Local processing, source traceability and task-specific measurement. |
| 5 | Project Plan with Timeline | Six documented phases; no fabricated implementation dates. |
| 6 | Literature Review | Research areas and the bounded implemented focus. |
| 7 | Gap in the Research / Technology / Methodology | Integration needs, evaluation needs and missing independent evidence. |
| 8 | Description of the Proposed Solution | Full editable architecture: capture, audio/slides, learned/rule paths, storage and review. |
| 9 | Requirement Analysis | Functional and operational requirements, with correction/recovery boundaries. |
| 10 | Technology Stack | Interface, service, audio/speakers, slides, classifiers, storage and reports. |
| 11 | Design: Discussion Detector | Feature extraction, classifier combination, smoothing and threshold. |
| 12 | Development / Implementation | Custom grouped partitions and development selection. |
| 13 | Testing & Debugging | Recorded 597-test run, retained negative trials and their limits. |
| 14 | Project Outcome: Discussion Detection | Matched F1 chart, installed precision/recall and uncertainty. |
| 15 | Project Outcome: Speech and Speakers | ASR improvement/regression by cohort and the custom speaker-calibration pilot. |
| 16 | Conclusion | Delivered prototype and remaining recording-level validation. |
| 17 | References | Selected literature; full 15-reference list in notes and the IEEE paper. |
| 18 | Photograph of the Presentation | Honest post-event slot for the real presentation photograph. |

The earlier 12-slide backup section and separate repeated explanations were removed. Useful technical detail remains in the notes, presenter guide and existing research report. There are no hidden backup slides or links to deleted slides. Most content uses native editable shapes, text, tables and chart bars; logos are images.

The architecture was checked against the current API, orchestrator, speech and discussion modules. The same waveform feeds recognition and diarization. Cached recognition words combine with final speaker intervals; they are not diarization input. The learned discussion path remains separate from final-decision anchors and exploratory influence. Arrows show dependencies, not simultaneous computation. Speaker renaming is distinguished from acoustic reclustering. The review edit loop returns to the application report, without implying that every raw disk export is rewritten.

Results retain their recorded values and scope: 53.54% discussion F1, 39.94% precision and 81.18% recall on human reference acts; a +1.46-point exploratory F1 difference over the matched forest; speech-model benefits and the English regression; and the small custom diarization pilot. There is no invented complete-project accuracy, significance claim or validated human influence score. The shared small speech model remains the default. Unsuccessful trials remain documented in the report.

The 14-minute speaking plan leaves one minute of transition buffer. All 18 slides have presenter notes and a suggested four-person handoff. Supplied contacts remain in cover notes and the guide. Every rendered slide was visually inspected, and automated checks validate the exact original heading order, slide count, cover label, layout, PDF text retention and reported metrics. Physical projection and live sound still require an in-room check. The real presentation photograph can only be added after the event.
