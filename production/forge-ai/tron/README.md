# Production Forge Tron AI repair

This directory contains only the production closure of the validated experimental Tron repair from PR #8.

## Validation provenance

- Experimental PR #8 validated head: `fd25362235521689e65b153998f8f58d016bd0b3`
- Phase-4 run: `33402270316`
- Final artifact: `9761801483`, SHA-256 `47f31986dc905e132704349aa0aaa27011e537d5ae8d30d3584fbd2a5e536071`
- Historical recovered AI provenance: `237300550e94586479bba9b1c6123af3e87cb179`

## Production dependency closure

The clean build starts from stock Forge 2.0.14 and compiles only five production classes:

1. `ComputerUtil` — Crop Rotation-specific real `chooseSacrificeType` entry integration.
2. `TronCropRotationSelection` — assembly-safe sacrifice identity filter.
3. `ComputerUtilCard` — validated missing-Tron-piece land selection plus land-sacrifice valuation used by the selector.
4. `ComputerUtilMana` — heterogeneous numeric-map normalization (`Number.intValue()`).
5. `PermanentAi` — MAIN1 allowance for Chromatic Star, Chromatic Sphere, and generic mana artifacts such as Energy Refractor.

`ChangeZoneAi` remains stock Forge 2.0.14 production code. The search plumbing still delegates land choice through `ComputerUtilCard`; PR #8's ChangeZone instrumentation was diagnostic only and is deliberately absent.

## Narrow rule

While resolving a Crop Rotation land sacrifice during Tron assembly, if another distinct Mine/Power Plant/Tower is missing and present in the library, unique controlled Tron pieces are removed from the sacrifice choice when a legal non-Tron land or duplicate Tron piece is available. If the assembly condition is not met, normal Forge behavior is used.

This preserves duplicate-piece sacrifice, missing-piece-unavailable fallback, full-Tron fallback, and legitimate nonassembly/same-piece cases.

## Explicit exclusions

No Hunting Storm behavior, Tinder Wall heuristic, Prismatic Strands, Supreme Verdict, Esper-specific logic, diagnostic telemetry, Gate workflow, experimental mode marker, generated log/result, Forge binary, deck edit, seed/card-ID/opponent-specific behavior, or failed integration attempt is included.

This PR changes Forge AI behavior only; it does not rebalance any Battle Box deck.
