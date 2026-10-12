#!/usr/bin/env bash
# Requires a running device/emulator and classes from bash android/build.sh.
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
SDK="${ANDROID_SDK_ROOT:-$HOME/Android/Sdk}"
mkdir -p android/build/probe-classes android/build/probe-dex
javac --release 8 -cp "$SDK/platforms/android-37.0/android.jar:android/build/classes" -d android/build/probe-classes android/test/MeetingAnalysisProbe.java
jar cf android/build/probe.jar -C android/build/probe-classes .
"$SDK/build-tools/36.0.0/d8" --lib "$SDK/platforms/android-37.0/android.jar" --min-api 26 --output android/build/probe-dex android/build/probe.jar android/build/classes.jar
"$SDK/platform-tools/adb" push android/build/probe-dex/classes.dex /data/local/tmp/mai-probe.dex
"$SDK/platform-tools/adb" shell 'CLASSPATH=/data/local/tmp/mai-probe.dex app_process /system/bin org.meetiq.offline.MeetingAnalysisProbe /data/local/tmp/mai-analysis-probe'
