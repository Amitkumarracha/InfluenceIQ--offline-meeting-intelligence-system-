#!/usr/bin/env bash
# Linux build using installed Android SDK tools; no Gradle/plugin download needed.
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
SDK="${ANDROID_SDK_ROOT:-$HOME/Android/Sdk}"
NDK="${ANDROID_NDK_HOME:-$PROJECT_DIR/.runtime/android-ndk-r26d}"
BUILD_TOOLS="${ANDROID_BUILD_TOOLS:-$SDK/build-tools/36.0.0}"
ANDROID_JAR="${ANDROID_JAR:-$SDK/platforms/android-37.0/android.jar}"
BUILD="$PROJECT_DIR/android/build"
CMAKE="$PROJECT_DIR/.venv/bin/cmake"
export PATH="$PROJECT_DIR/.venv/bin:$PATH"
mkdir -p "$BUILD/classes" "$BUILD/dex" "$BUILD/apk/lib"
for ABI in arm64-v8a x86_64; do
    "$CMAKE" -S android/app/src/main/cpp -B "$BUILD/$ABI" -G Ninja \
        -DCMAKE_TOOLCHAIN_FILE="$NDK/build/cmake/android.toolchain.cmake" \
        -DANDROID_ABI="$ABI" -DANDROID_PLATFORM=android-26 -DANDROID_STL=c++_static -DCMAKE_BUILD_TYPE=Release
    "$CMAKE" --build "$BUILD/$ABI" --target meetiq --parallel 4
    mkdir -p "$BUILD/apk/lib/$ABI"
    cp "$BUILD/$ABI/libmeetiq.so" "$BUILD/apk/lib/$ABI/"
done
javac --release 8 -classpath "$ANDROID_JAR" -d "$BUILD/classes" android/app/src/main/java/org/meetiq/offline/*.java
jar cf "$BUILD/classes.jar" -C "$BUILD/classes" .
"$BUILD_TOOLS/d8" --lib "$ANDROID_JAR" --min-api 26 --output "$BUILD/dex" "$BUILD/classes.jar"
"$BUILD_TOOLS/aapt2" link -o "$BUILD/unsigned.apk" -I "$ANDROID_JAR" \
    --manifest android/app/src/main/AndroidManifest.xml --debug-mode -A android/app/src/main/assets
cp "$BUILD/dex/classes.dex" "$BUILD/apk/"
python3 - "$BUILD" <<'PYZIP'
import sys, zipfile
from pathlib import Path
build = Path(sys.argv[1])
with zipfile.ZipFile(build / 'unsigned.apk', 'a', compression=zipfile.ZIP_DEFLATED) as archive:
    for source in (build / 'apk').rglob('*'):
        if source.is_file():
            archive.write(source, source.relative_to(build / 'apk'))
PYZIP
"$BUILD_TOOLS/zipalign" -f -P 16 4 "$BUILD/unsigned.apk" "$BUILD/aligned.apk"
if [ ! -f "$PROJECT_DIR/.runtime/android-debug.keystore" ]; then
    keytool -genkeypair -keystore "$PROJECT_DIR/.runtime/android-debug.keystore" -storepass android \
        -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 -validity 10000 \
        -dname 'CN=Meet IQ Development'
fi
"$BUILD_TOOLS/apksigner" sign --ks "$PROJECT_DIR/.runtime/android-debug.keystore" --ks-pass pass:android \
    --out "$BUILD/meet-iq-debug.apk" "$BUILD/aligned.apk"
"$BUILD_TOOLS/apksigner" verify "$BUILD/meet-iq-debug.apk"
echo "Built: $BUILD/meet-iq-debug.apk"
