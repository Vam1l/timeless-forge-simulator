#!/usr/bin/env bash
set -e

FORGE_JAR=${1:-"forge-2.0.14.jar"}

if [ ! -f "$FORGE_JAR" ]; then
    echo "Error: $FORGE_JAR not found."
    exit 1
fi

BUILD_DIR=$(mktemp -d)
trap 'rm -rf "$BUILD_DIR"' EXIT

echo "Compiling Forge AI patches against $FORGE_JAR..."
javac -cp "$FORGE_JAR" \
  forge-patches/forge/ai/ability/TokenAi.java \
  forge-patches/forge/ai/ability/ManaAi.java \
  forge-patches/forge/ai/ability/ChangeZoneAi.java \
  forge-patches/forge/ai/ability/DestroyAllAi.java \
  forge-patches/forge/ai/ability/TwoPilesAi.java \
  forge-patches/forge/ai/ability/ChooseColorAi.java \
  forge-patches/forge/ai/ability/PermanentAi.java \
  forge-patches/forge/ai/ComputerUtilCard.java \
  forge-patches/forge/ai/ComputerUtilMana.java \
  forge-patches/forge/ai/PlayerControllerAi.java \
  forge-patches/forge/game/ability/effects/TwoPilesEffect.java \
  -d "$BUILD_DIR"

echo "Updating $FORGE_JAR with compiled class files..."
jar uf "$FORGE_JAR" -C "$BUILD_DIR" .
echo "Successfully patched $FORGE_JAR"
