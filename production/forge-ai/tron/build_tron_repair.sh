#!/usr/bin/env bash
set -euo pipefail

STOCK_JAR=${1:?stock Forge 2.0.14 jar required}
SOURCE_ROOT=${2:?exact Forge 2.0.14 source root required}
OUT_JAR=${3:?output jar required}
BUILD_DIR=${4:-build/tron-ai-repair}

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/src/forge/ai/ability" "$BUILD_DIR/classes"
cp "$STOCK_JAR" "$OUT_JAR"

python production/forge-ai/tron/apply_computer_util.py \
  --input "$SOURCE_ROOT/forge/ai/ComputerUtil.java" \
  --output "$BUILD_DIR/src/forge/ai/ComputerUtil.java"
python production/forge-ai/tron/apply_tron_support.py \
  --source-dir "$SOURCE_ROOT" --output-dir "$BUILD_DIR/src"
cp production/forge-ai/tron/TronCropRotationSelection.java "$BUILD_DIR/src/forge/ai/TronCropRotationSelection.java"

javac -cp "$STOCK_JAR" \
  "$BUILD_DIR/src/forge/ai/TronCropRotationSelection.java" \
  "$BUILD_DIR/src/forge/ai/ComputerUtil.java" \
  "$BUILD_DIR/src/forge/ai/ComputerUtilCard.java" \
  "$BUILD_DIR/src/forge/ai/ComputerUtilMana.java" \
  "$BUILD_DIR/src/forge/ai/ability/PermanentAi.java" \
  -d "$BUILD_DIR/classes"

jar uf "$OUT_JAR" \
  -C "$BUILD_DIR/classes" forge/ai/TronCropRotationSelection.class \
  -C "$BUILD_DIR/classes" forge/ai/ComputerUtil.class \
  -C "$BUILD_DIR/classes" forge/ai/ComputerUtilCard.class \
  -C "$BUILD_DIR/classes" forge/ai/ComputerUtilMana.class \
  -C "$BUILD_DIR/classes" forge/ai/ability/PermanentAi.class

sha256sum "$STOCK_JAR" "$OUT_JAR" > "$BUILD_DIR/jar-sha256.txt"
