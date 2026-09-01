# Production Cleansing Wildfire AI repair

This directory contains the clean production form of the Cleansing Wildfire targeting repair validated experimentally in PR #11. The production implementation is reconstructed from production `main`; the experimental PR is evidence only and is not merged or cherry-picked.

For the exact Forge 2.0.14 Cleansing Wildfire `Destroy -> optional basic-land search for TargetedController -> Draw` structure, the AI considers all legal battlefield land targets. If two or more distinct legal opposing Urza Mine/Power Plant/Tower names are visible, it preserves land disruption using Forge's existing land-removal ranking. Otherwise it prefers a legal own indestructible land. If neither condition applies, stock `DestroyAi` targeting continues unchanged.

The production closure contains no experimental telemetry, SpellAbility identity logging, MagicStack instrumentation, measurement parser, simulation corpus, deck-specific logic, or compiled artifacts. It composes with the existing production Tron repair without modifying that repair.

Validation reference: gameplay baseline `4a68cef04883eb029041371d738bb004bc3a95bb`; measurement validation run `33545165716` confirmed the experimental telemetry was removable without changing gameplay behavior.
