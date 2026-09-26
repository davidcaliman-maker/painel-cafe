#!/usr/bin/env bash
# Gera o APK sem Gradle, usando apenas o Android SDK local (build-tools 30 + android-30).
# Uso (Git Bash):  ./build-apk.sh      ->  saída em build/PainelCafe.apk
set -euo pipefail
cd "$(dirname "$0")"

SDK="${ANDROID_HOME:-$LOCALAPPDATA/Android/Sdk}"
BT="$SDK/build-tools/30.0.0"
JAR="$SDK/platforms/android-30/android.jar"
SRC=app/src/main
OUT=build

rm -rf "$OUT" && mkdir -p "$OUT/res" "$OUT/gen" "$OUT/classes" "$OUT/dex"

# O manifest do Gradle usa "namespace"; o aapt2 precisa do atributo package.
sed 's|<manifest |<manifest package="br.painelcafe" |' "$SRC/AndroidManifest.xml" > "$OUT/AndroidManifest.xml"

"$BT/aapt2" compile --dir "$SRC/res" -o "$OUT/res/res.zip"
"$BT/aapt2" link -o "$OUT/unsigned.apk" -I "$JAR" \
  --manifest "$OUT/AndroidManifest.xml" -A "$SRC/assets" \
  --java "$OUT/gen" --min-sdk-version 24 --target-sdk-version 30 \
  --version-code 8 --version-name 3.0 "$OUT/res/res.zip"

javac -encoding UTF-8 --release 8 -classpath "$JAR" -d "$OUT/classes" \
  $(find "$SRC/java" "$OUT/gen" -name '*.java')

java -cp "$BT/lib/d8.jar" com.android.tools.r8.D8 --release --min-api 24 --lib "$JAR" --output "$OUT/dex" $(find "$OUT/classes" -name '*.class')

cp "$OUT/unsigned.apk" "$OUT/with-dex.apk"
jar uf "$OUT/with-dex.apk" -C "$OUT/dex" classes.dex

"$BT/zipalign" -f 4 "$OUT/with-dex.apk" "$OUT/aligned.apk"
java -jar "$BT/lib/apksigner.jar" sign --ks "$HOME/.android/debug.keystore" --ks-pass pass:android \
  --key-pass pass:android --ks-key-alias androiddebugkey --out "$OUT/PainelCafe.apk" "$OUT/aligned.apk"

echo "APK gerado: $OUT/PainelCafe.apk"
