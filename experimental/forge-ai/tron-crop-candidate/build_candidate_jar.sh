#!/usr/bin/env bash
set -euo pipefail

RECOVERED_JAR=${1:?exact recovered jar required}
STOCK_COMPUTER_UTIL=${2:?stock Forge 2.0.14 ComputerUtil.java required}
RECOVERED_CHANGEZONE=${3:?immutable recovered ChangeZoneAi.java required}
RECOVERED_DIAG_JAR=${4:?recovered diagnostic jar required}
CANDIDATE_JAR=${5:?candidate output jar required}
OUT_DIR=${6:?output directory required}

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/recovered/src/forge/ai/ability" "$OUT_DIR/recovered/classes"
mkdir -p "$OUT_DIR/candidate/src/forge/ai/ability" "$OUT_DIR/candidate/classes"
cp "$RECOVERED_JAR" "$RECOVERED_DIAG_JAR"
cp "$RECOVERED_JAR" "$CANDIDATE_JAR"

for mode in recovered candidate; do
  python experimental/forge-ai/tron-crop-candidate/apply_candidate_overlay.py \
    --input "$STOCK_COMPUTER_UTIL" \
    --output "$OUT_DIR/$mode/src/forge/ai/ComputerUtil.java" \
    --mode "$mode" \
    --diff "$OUT_DIR/$mode-computerutil-overlay.diff"
  python experimental/forge-ai/tron-crop-candidate/apply_fetch_telemetry.py \
    --input "$RECOVERED_CHANGEZONE" \
    --output "$OUT_DIR/$mode/src/forge/ai/ability/ChangeZoneAi.java" \
    --diff "$OUT_DIR/$mode-changezone-telemetry.diff"
  cp experimental/forge-ai/tron-crop-candidate/TronCropRotationSelection.java \
    "$OUT_DIR/$mode/src/forge/ai/TronCropRotationSelection.java"
done

javac -cp "$RECOVERED_JAR" \
  "$OUT_DIR/recovered/src/forge/ai/TronCropRotationSelection.java" \
  "$OUT_DIR/recovered/src/forge/ai/ComputerUtil.java" \
  "$OUT_DIR/recovered/src/forge/ai/ability/ChangeZoneAi.java" \
  -d "$OUT_DIR/recovered/classes"

javac -cp "$RECOVERED_JAR" \
  "$OUT_DIR/candidate/src/forge/ai/TronCropRotationSelection.java" \
  "$OUT_DIR/candidate/src/forge/ai/ComputerUtil.java" \
  "$OUT_DIR/candidate/src/forge/ai/ability/ChangeZoneAi.java" \
  -d "$OUT_DIR/candidate/classes"

jar uf "$RECOVERED_DIAG_JAR" -C "$OUT_DIR/recovered/classes" forge/ai/ComputerUtil.class
jar uf "$RECOVERED_DIAG_JAR" -C "$OUT_DIR/recovered/classes" forge/ai/TronCropRotationSelection.class
jar uf "$RECOVERED_DIAG_JAR" -C "$OUT_DIR/recovered/classes" forge/ai/ability/ChangeZoneAi.class

jar uf "$CANDIDATE_JAR" -C "$OUT_DIR/candidate/classes" forge/ai/ComputerUtil.class
jar uf "$CANDIDATE_JAR" -C "$OUT_DIR/candidate/classes" forge/ai/TronCropRotationSelection.class
jar uf "$CANDIDATE_JAR" -C "$OUT_DIR/candidate/classes" forge/ai/ability/ChangeZoneAi.class

sha256sum "$RECOVERED_JAR" "$RECOVERED_DIAG_JAR" "$CANDIDATE_JAR" > "$OUT_DIR/build-sha256.txt"
