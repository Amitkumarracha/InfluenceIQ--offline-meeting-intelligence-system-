#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
mkdir -p android/build/test-classes
javac --release 8 -d android/build/test-classes android/app/src/main/java/org/meetiq/offline/json/*.java android/app/src/main/java/org/meetiq/offline/analysis/*.java android/test/*.java
java -cp android/build/test-classes org.meetiq.offline.test.AnalysisParityTest
