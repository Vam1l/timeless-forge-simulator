#!/usr/bin/env bash
set -euo pipefail

STOCK_JAR=${1:?stock Forge 2.0.14 jar required}
SOURCE_ROOT=${2:?exact Forge 2.0.14 source root required}
PRODUCTION_JAR=${3:?production output jar required}
CANDIDATE_JAR=${4:?candidate output jar required}
BUILD_DIR=${5:-build/jund-cleansing-wildfire}

rm -rf "$BUILD_DIR"
mkdir -p \
  "$BUILD_DIR/behavior-baseline/forge/ai/ability" \
  "$BUILD_DIR/candidate-src/forge/ai/ability" \
  "$BUILD_DIR/candidate-src/forge/game/zone" \
  "$BUILD_DIR/verification" \
  "$BUILD_DIR/candidate-classes" \
  "$BUILD_DIR/policy-test"

# Build the exact current production Forge first; this preserves the merged Tron
# Crop Rotation repair and numeric-map normalization byte-for-byte in the candidate.
bash production/forge-ai/tron/build_tron_repair.sh \
  "$STOCK_JAR" "$SOURCE_ROOT" "$PRODUCTION_JAR" "$BUILD_DIR/production"
cp "$PRODUCTION_JAR" "$CANDIDATE_JAR"

# Generate the exact PR #11 gameplay-bearing DestroyAi before adding measurement.
python experimental/forge-ai/jund-cleansing-wildfire/apply_destroy_ai_candidate.py \
  --input "$SOURCE_ROOT/forge/ai/ability/DestroyAi.java" \
  --output "$BUILD_DIR/behavior-baseline/forge/ai/ability/DestroyAi.java"

# Add reversible diagnostic-only overlays to DestroyAi and the actual stack
# commitment boundary. The overlay verifies that stripping its measurement code
# reproduces the inputs byte-for-byte.
python experimental/forge-ai/jund-cleansing-wildfire/apply_measurement_telemetry.py \
  --destroy-input "$BUILD_DIR/behavior-baseline/forge/ai/ability/DestroyAi.java" \
  --destroy-output "$BUILD_DIR/candidate-src/forge/ai/ability/DestroyAi.java" \
  --stack-input "$SOURCE_ROOT/forge/game/zone/MagicStack.java" \
  --stack-output "$BUILD_DIR/candidate-src/forge/game/zone/MagicStack.java" \
  --verify-destroy-output "$BUILD_DIR/verification/DestroyAi.behavior.java" \
  --verify-stack-output "$BUILD_DIR/verification/MagicStack.behavior.java"
cmp "$BUILD_DIR/behavior-baseline/forge/ai/ability/DestroyAi.java" \
    "$BUILD_DIR/verification/DestroyAi.behavior.java"
cmp "$SOURCE_ROOT/forge/game/zone/MagicStack.java" \
    "$BUILD_DIR/verification/MagicStack.behavior.java"

cp experimental/forge-ai/jund-cleansing-wildfire/CleansingWildfireTargetingPolicy.java \
  "$BUILD_DIR/candidate-src/forge/ai/ability/CleansingWildfireTargetingPolicy.java"

# Deterministic policy tests remain exactly the PR #11 tests and execute before
# any gameplay.
javac -d "$BUILD_DIR/policy-test" \
  experimental/forge-ai/jund-cleansing-wildfire/CleansingWildfireTargetingPolicy.java \
  experimental/forge-ai/jund-cleansing-wildfire/CleansingWildfireTargetingPolicyTest.java
java -cp "$BUILD_DIR/policy-test" forge.ai.ability.CleansingWildfireTargetingPolicyTest \
  | tee "$BUILD_DIR/policy-test.txt"

# Compile the unchanged policy/DestroyAi behavior plus logging-only telemetry.
javac -cp "$PRODUCTION_JAR" \
  "$BUILD_DIR/candidate-src/forge/ai/ability/CleansingWildfireTargetingPolicy.java" \
  "$BUILD_DIR/candidate-src/forge/ai/ability/DestroyAi.java" \
  "$BUILD_DIR/candidate-src/forge/game/zone/MagicStack.java" \
  -d "$BUILD_DIR/candidate-classes"

jar uf "$CANDIDATE_JAR" \
  -C "$BUILD_DIR/candidate-classes" forge/ai/ability/CleansingWildfireTargetingPolicy.class \
  -C "$BUILD_DIR/candidate-classes" forge/ai/ability/CleansingWildfireTargetingPolicy\$Decision.class \
  -C "$BUILD_DIR/candidate-classes" forge/ai/ability/DestroyAi.class \
  -C "$BUILD_DIR/candidate-classes" forge/game/zone/MagicStack.class

sha256sum "$STOCK_JAR" "$PRODUCTION_JAR" "$CANDIDATE_JAR" > "$BUILD_DIR/jar-sha256.txt"
