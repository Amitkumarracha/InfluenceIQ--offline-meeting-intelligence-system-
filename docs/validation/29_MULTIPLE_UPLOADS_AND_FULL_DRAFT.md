# Multiple uploads and complete processing transcript

Audio selections now append to the current list instead of replacing it. Users can select several files at once or add files from separate folders. The listed audio order is the concatenation order; items can be moved up or removed. The upload API retains its 32-audio-part limit and FFmpeg normalises each part independently.

Presentation selection now supports up to 32 PPTX files, including additions across selections, ordering and removal. The API validates every deck before queueing. The worker extracts decks in order, assigns unique global slide numbers/IDs and retains source deck and original slide number in slide metadata. A malformed later deck causes the whole upload to be cleaned up. Previously saved jobs with a single PPT path remain compatible. Binary `.ppt` still requires conversion to `.pptx`.

The ASR callbacks now deliver all completed passages on fresh, cached-chunk and final-cache paths. The pipeline saves the complete draft; the processing view displays “Transcript so far — from the beginning” in a scrollable panel. Draft NLP candidate extraction remains bounded to recent passages; this does not trim displayed transcript text.

Checks: `tests/test_multiple_uploads.py` verifies real mixed-rate audio concatenation, API multipart intake, two-deck extraction, legacy single-deck compatibility, rollback on invalid second deck, and full transcript snapshots above 50 passages across fresh/resumed/cached execution. The browser workflow covers adding audio and decks, presentation reordering, multipart submission and 75 visible draft passages. Test artifacts: `.runtime/validation/multiple-uploads-*`.

Uploaded audio parts represent one meeting and are joined; these controls do not create separate jobs for unrelated meetings. Presentation order does not establish actual slide display timestamps. Existing older draft files acquire complete text on the next run with the updated worker.

Validation result: 563 Python tests passed (7 dependency warnings); frontend lint/build passed; browser workflow passed with no page errors at 360, 390, 960 and 1440 pixel widths. The backend was restarted only after confirming no queued/processing jobs; health and local speech/speaker models were ready afterward.
