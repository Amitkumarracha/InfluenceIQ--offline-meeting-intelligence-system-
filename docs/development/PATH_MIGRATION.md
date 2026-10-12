# File relocation — 8 October 2026

[Master documentation](../README.md)

Application paths were repaired after these moves. The submitted report content was preserved byte for byte. Archive entries preserve comparison/history, rather than active launch commands.

| Previous path | Current path |
| --- | --- |
| `api.py` | `backend/api.py` |
| `config.yaml` | `config/config.yaml` |
| `.env` | `config/.env` |
| `.env.example` | `config/.env.example` |
| `pytest.ini` | `config/pytest.ini` |
| `requirements.txt` | `environment/requirements.txt` |
| `requirements-lock.txt` | `environment/requirements-lock.txt` |
| `start_app.sh` | `scripts/start_app.sh` |
| `create_test_samples.py` | `scripts/create_test_samples.py` |
| `run_resume_pipeline.sh` | `archive/legacy_tools/run_resume_pipeline.sh` |
| `run_single_test.sh` | `archive/legacy_tools/run_single_test.sh` |
| `run_small_chunk.py` | `archive/legacy_tools/run_small_chunk.py` |
| `terminal output ` | `archive/legacy_logs/terminal_output.txt` |
| `efficiency-results.json` | `outputs/evaluation/efficiency-results.json` |
| `validation-results.json` | `outputs/evaluation/validation-results.json` |
| `README.md` | `docs/guides/QUICK_START.md` |
| `RUN_MANUALLY.md` | `docs/guides/RUN_MANUALLY.md` |
| `PROJECT_STATUS.md` | `docs/validation/PROJECT_STATUS.md` |
| `EFFICIENCY_IMPROVEMENTS.md` | `docs/validation/EFFICIENCY_IMPROVEMENTS.md` |
| `AUDIO_ONLY_CONVERSION_GUIDE.md` | `docs/history/AUDIO_ONLY_CONVERSION_GUIDE.md` |
| `NEXT_STEPS.md` | `docs/history/NEXT_STEPS.md` |
| `PROJECT_EXECUTION_GUIDE.md` | `docs/history/PROJECT_EXECUTION_GUIDE.md` |
| `REPOSITORY_REVIEW.md` | `docs/history/REPOSITORY_REVIEW.md` |
| `android/README.md` | `docs/android/README.md` |
| `android/DESIGN.md` | `docs/android/DESIGN.md` |
| `my_report_submitted/GRPUP_NO_12_MAI_REPORT_1_LLM.md` | `docs/submitted/GRPUP_NO_12_MAI_REPORT_1_LLM.md` |
| `notebooks/README.md` | `docs/development/NOTEBOOKS.md` |
| `research_developer_docs/README.md` | `docs/handbook/README.md` |
| `research_developer_docs/11_EVALUATION_BASELINES_AND_ABLATIONS.md` | `docs/research/11_EVALUATION_BASELINES_AND_ABLATIONS.md` |
| `research_developer_docs/02_FOLDER_STRUCTURE.md` | `docs/development/02_FOLDER_STRUCTURE.md` |
| `research_developer_docs/18_SUBMITTED_REPORT_FEEDBACK_AND_NLP_DELIVERY.md` | `docs/validation/18_SUBMITTED_REPORT_FEEDBACK_AND_NLP_DELIVERY.md` |
| `research_developer_docs/05_AUDIO_IMPLEMENTATION.md` | `docs/development/05_AUDIO_IMPLEMENTATION.md` |
| `research_developer_docs/09_DATA_OUTPUTS_AND_RESULTS.md` | `docs/validation/09_DATA_OUTPUTS_AND_RESULTS.md` |
| `research_developer_docs/19_ANDROID_SPEAKERS_FUSION_AND_VALIDATION.md` | `docs/validation/19_ANDROID_SPEAKERS_FUSION_AND_VALIDATION.md` |
| `research_developer_docs/08_APPLICATIONS_API_FRONTEND_ANDROID.md` | `docs/development/08_APPLICATIONS_API_FRONTEND_ANDROID.md` |
| `research_developer_docs/04_ARCHITECTURE_AND_PIPELINE.md` | `docs/development/04_ARCHITECTURE_AND_PIPELINE.md` |
| `research_developer_docs/13_DEVELOPER_HANDOVER_AND_GAPS.md` | `docs/development/13_DEVELOPER_HANDOVER_AND_GAPS.md` |
| `research_developer_docs/07_EVENTS_DECISIONS_INTERACTIONS_INFLUENCE.md` | `docs/development/07_EVENTS_DECISIONS_INTERACTIONS_INFLUENCE.md` |
| `research_developer_docs/16_AUDIT_PROVENANCE_AND_VALIDATION.md` | `docs/validation/16_AUDIT_PROVENANCE_AND_VALIDATION.md` |
| `research_developer_docs/15_SOURCE_CODE_REFERENCE.md` | `docs/development/15_SOURCE_CODE_REFERENCE.md` |
| `research_developer_docs/03_ENVIRONMENT_AND_SETUP.md` | `docs/development/03_ENVIRONMENT_AND_SETUP.md` |
| `research_developer_docs/14_FILE_BY_FILE_COMPARISON.md` | `docs/validation/14_FILE_BY_FILE_COMPARISON.md` |
| `research_developer_docs/17_MINIMAL_UI_IMPLEMENTATION_AND_VALIDATION.md` | `docs/validation/17_MINIMAL_UI_IMPLEMENTATION_AND_VALIDATION.md` |
| `research_developer_docs/10_RESEARCH_NOVELTY_AND_RELATED_WORK.md` | `docs/research/10_RESEARCH_NOVELTY_AND_RELATED_WORK.md` |
| `research_developer_docs/01_PROJECT_HISTORY_AND_COMPARISON.md` | `docs/research/01_PROJECT_HISTORY_AND_COMPARISON.md` |
| `research_developer_docs/21_OFFLINE_AND_WORKSTATION_DEPLOYMENT.md` | `docs/operations/21_OFFLINE_AND_WORKSTATION_DEPLOYMENT.md` |
| `research_developer_docs/12_JOURNAL_PAPER_BLUEPRINT.md` | `docs/research/12_JOURNAL_PAPER_BLUEPRINT.md` |
| `research_developer_docs/20_TRAINING_DATA_AND_MULTIMODAL_RESEARCH.md` | `docs/research/20_TRAINING_DATA_AND_MULTIMODAL_RESEARCH.md` |
| `research_developer_docs/06_FUSION_METHODS.md` | `docs/research/06_FUSION_METHODS.md` |

`nexus_v2.db` additionally moved to `data/state/nexus_v2.db`; a pre-move SQLite backup is in `archive/legacy_state/before_reorganization.db`. The old unused `nexus.db` is in `archive/legacy_state/`.
