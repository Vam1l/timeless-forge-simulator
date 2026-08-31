# Tron Crop Rotation Phase 4 verification v3

Behavioral baseline for this verification is commit `dc9f9c38c3626f5b2d112152c3d36c5139dd1ee1`.

This iteration does **not** change the candidate selector, its integration into `ComputerUtil.chooseSacrificeType`, any AI threshold, mana behavior, deck, random call, or historical recovered blob. It only corrects observational fetch telemetry and validation/reporting.

## Why the previous fetch telemetry missed the real selection

Forge 2.0.14 `ChangeZoneAi.chooseCardToHiddenOriginChangeZone` handles a Library-to-Battlefield search in an earlier `Battlefield/Graveyard` branch. Crop Rotation therefore selected its land through `ComputerUtilCard.getBestAI(fetchList)` and then reached the method's common final return. The old `[TRON_CROP_FETCH]` statement was attached only to the later `getBestLandAI` fallback, so it never observed the actual seed-95001 fetch.

The corrected telemetry labels the unchanged selection path and emits `[TRON_CROP_FETCH]` at the common final return. It also logs the key-card early returns that can bypass that boundary. The selected `Card` object and every selection expression remain unchanged.

## Verification gates

1. One candidate-only seed-95001 Tron-vs-White game must show the already-proven real sacrifice selector, actual Forest sacrifice, preserved Mine, and a direct fetch event selecting an available different missing Tron piece.
2. Existing selector tests, real-entry source guards, fetch-parser/path tests, and Byte/Integer normalization checks must pass.
3. Only then run the six matched Tron conditions on recovered control and candidate plus the two matched non-Tron smoke conditions, exactly 16 games.

No win-rate criterion is used. No third behavioral repair is authorized by this verification.
