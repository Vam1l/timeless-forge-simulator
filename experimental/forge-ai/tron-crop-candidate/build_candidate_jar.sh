#!/usr/bin/env bash
set -euo pipefail

RECOVERED_JAR=${1:?recovered jar required}
STOCK_COMPUTER_UTIL=${2:?stock Forge 2.0.14 ComputerUtil.java required}
OUT_JAR=${3:?candidate output jar required}
OUT_DIR=${4:?output directory required}

mkdir -p "$OUT_DIR/src/forge/ai" "$OUT_DIR/classes"
cp "$RECOVERED_JAR" "$OUT_JAR"

python experimental/forge-ai/tron-crop-candidate/apply_candidate_overlay.py \
  --input "$STOCK_COMPUTER_UTIL" \
  --output "$OUT_DIR/src/forge/ai/ComputerUtil.java" \
  --diff "$OUT_DIR/candidate-overlay.diff"
cp experimental/forge-ai/tron-crop-candidate/TronCropRotationSelection.java \
  "$OUT_DIR/src/forge/ai/TronCropRotationSelection.java"

javac -cp "$RECOVERED_JAR" \
  "$OUT_DIR/src/forge/ai/TronCropRotationSelection.java" \
  "$OUT_DIR/src/forge/ai/ComputerUtil.java" \
  -d "$OUT_DIR/classes"

jar uf "$OUT_JAR" -C "$OUT_DIR/classes" forge/ai/ComputerUtil.class
jar uf "$OUT_JAR" -C "$OUT_DIR/classes" forge/ai/TronCropRotationSelection.class
sha256sum "$RECOVERED_JAR" "$OUT_JAR" > "$OUT_DIR/recovered-candidate-sha256.txt"
