#!/usr/bin/env bash
set -euo pipefail

STOCK_JAR=${1:?stock Forge 2.0.14 jar required}
SOURCE_ROOT=${2:?exact Forge 2.0.14 source root required}
OUT_JAR=${3:?production output jar required}
BUILD_DIR=${4:-build/cleansing-wildfire-production}

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/wildfire-src/forge/ai/ability" "$BUILD_DIR/wildfire-classes" "$BUILD_DIR/policy-test"

# Build the exact current production Tron repair first, then layer only the
# validated Cleansing Wildfire DestroyAi override.
bash production/forge-ai/tron/build_tron_repair.sh \
  "$STOCK_JAR" "$SOURCE_ROOT" "$OUT_JAR" "$BUILD_DIR/tron"

python production/forge-ai/cleansing-wildfire/apply_destroy_ai.py \
  --input "$SOURCE_ROOT/forge/ai/ability/DestroyAi.java" \
  --output "$BUILD_DIR/wildfire-src/forge/ai/ability/DestroyAi.java"
cp production/forge-ai/cleansing-wildfire/CleansingWildfireTargetingPolicy.java \
  "$BUILD_DIR/wildfire-src/forge/ai/ability/CleansingWildfireTargetingPolicy.java"

javac -d "$BUILD_DIR/policy-test" \
  production/forge-ai/cleansing-wildfire/CleansingWildfireTargetingPolicy.java \
  production/forge-ai/cleansing-wildfire/CleansingWildfireTargetingPolicyTest.java
java -cp "$BUILD_DIR/policy-test" forge.ai.ability.CleansingWildfireTargetingPolicyTest \
  | tee "$BUILD_DIR/policy-test.txt"

javac -cp "$OUT_JAR" \
  "$BUILD_DIR/wildfire-src/forge/ai/ability/CleansingWildfireTargetingPolicy.java" \
  "$BUILD_DIR/wildfire-src/forge/ai/ability/DestroyAi.java" \
  -d "$BUILD_DIR/wildfire-classes"

jar uf "$OUT_JAR" \
  -C "$BUILD_DIR/wildfire-classes" forge/ai/ability/CleansingWildfireTargetingPolicy.class \
  -C "$BUILD_DIR/wildfire-classes" forge/ai/ability/CleansingWildfireTargetingPolicy\$Decision.class \
  -C "$BUILD_DIR/wildfire-classes" forge/ai/ability/DestroyAi.class

sha256sum "$STOCK_JAR" "$OUT_JAR" > "$BUILD_DIR/jar-sha256.txt"
