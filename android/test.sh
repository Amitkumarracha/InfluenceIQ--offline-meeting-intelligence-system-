#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
mkdir -p android/build/test-classes
javac --release 8 -d android/build/test-classes android/app/src/main/java/org/meetiq/offline/SyncAddress.java android/test/SyncAddressTest.java
java -cp android/build/test-classes org.meetiq.offline.SyncAddressTest
javac --release 8 -d android/build/test-classes android/app/src/main/java/org/meetiq/offline/WavAudio.java android/app/src/main/java/org/meetiq/offline/PcmAudio.java android/test/WavAudioTest.java
java -cp android/build/test-classes org.meetiq.offline.test.WavAudioTest
javac --release 8 -cp android/build/test-classes -d android/build/test-classes android/app/src/main/java/org/meetiq/offline/Vocabulary.java android/app/src/main/java/org/meetiq/offline/PresentationText.java android/test/MeetingInputTest.java
java -cp android/build/test-classes org.meetiq.offline.test.MeetingInputTest
javac --release 8 -d android/build/test-classes android/app/src/main/java/org/meetiq/offline/MeetingProgress.java android/app/src/main/java/org/meetiq/offline/SpeakerBudget.java android/test/MeetingProgressTest.java
java -cp android/build/test-classes org.meetiq.offline.MeetingProgressTest
javac --release 8 -d android/build/test-classes android/app/src/main/java/org/meetiq/offline/ModelFile.java android/test/ModelFileTest.java
java -cp android/build/test-classes org.meetiq.offline.ModelFileTest models/ggml-base.bin

.venv/bin/python scripts/export_event_rules.py
.venv/bin/python - <<'PYRULES'
import json
from pathlib import Path
rows = []
for kind, name in [('allow', 'event_patterns.json'), ('block', 'event_blockers.json')]:
    data = json.loads((Path('android/app/src/main/assets') / name).read_text())
    rows.extend(kind + '\t' + key + '\t' + pattern for key, patterns in data.items() for pattern in patterns)
Path('android/build/event-rules-test.tsv').write_text('\n'.join(rows), encoding='utf-8')
PYRULES
javac --release 8 -d android/build/test-classes android/app/src/main/java/org/meetiq/offline/EventRules.java android/test/EventRulesTest.java
java -cp android/build/test-classes org.meetiq.offline.EventRulesTest android/build/event-rules-test.tsv
javac --release 8 -d android/build/test-classes android/app/src/main/java/org/meetiq/offline/SlideIndex.java android/app/src/main/java/org/meetiq/offline/SpeakerAttribution.java android/test/AnalysisMathTest.java
java -cp android/build/test-classes org.meetiq.offline.AnalysisMathTest
