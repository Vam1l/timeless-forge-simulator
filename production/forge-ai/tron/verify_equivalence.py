#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def block(text: str, start: str, end: str) -> str:
    i = text.find(start)
    j = text.find(end, i)
    if i < 0 or j < 0:
        raise SystemExit(f'block not found: {start!r} .. {end!r}')
    return text[i:j]


def add(rows, component, mode, checks, **meta):
    rows.append({
        'component': component,
        'mode': mode,
        'checks': checks,
        'equivalent': all(checks.values()),
        **meta,
    })


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--production-dir', type=Path, required=True)
    p.add_argument('--validated-dir', type=Path, required=True)
    p.add_argument('--production-selector', type=Path, required=True)
    p.add_argument('--validated-selector', type=Path, required=True)
    p.add_argument('--production-selector-test', type=Path, required=True)
    p.add_argument('--validated-selector-test', type=Path, required=True)
    p.add_argument('--stock-changezone', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    prod, val, rows = a.production_dir, a.validated_dir, []

    for component, production, validated in (
        ('TronCropRotationSelection', a.production_selector, a.validated_selector),
        ('TronCropRotationSelectionTest', a.production_selector_test, a.validated_selector_test),
    ):
        add(rows, component, 'exact_source',
            {'source_bytes_equal': production.read_bytes() == validated.read_bytes()},
            production_sha256=sha(production), validated_sha256=sha(validated))

    pm = (prod / 'forge/ai/ComputerUtilMana.java').read_text()
    vm = (val / 'ComputerUtilMana.java').read_text()
    start = '            for (Object key : manaAbilityMap.keySet()) {\n'
    end = '                    if (res.get(shard).contains(sa)) continue;\n'
    pb, vb = block(pm, start, end), block(vm, start, end)
    add(rows, 'ComputerUtilMana', 'exact_repair_source', {
        'numeric_repair_block_exact': pb == vb,
        'number_guard': 'if (!(key instanceof Number)) continue;' in pb,
        'number_int_value': 'int colorVal = ((Number) key).intValue();' in pb,
        'lookup_uses_normalized_integer': 'manaAbilityMap.get(colorVal)' in pb,
        'typed_integer_multimap': 'ListMultimap<Integer, SpellAbility> manaMap = ArrayListMultimap.create();' in pm,
        'color_keys_normalized_to_integer': 'manaMap.put((int)' in pm,
    }, production_repair_sha256=hashlib.sha256(pb.encode()).hexdigest(),
       validated_repair_sha256=hashlib.sha256(vb.encode()).hexdigest(),
       compiled_class_equivalence='whole-class comparison not meaningful because production starts from stock source and carries only the audited generic repair')

    cu = (prod / 'forge/ai/ComputerUtil.java').read_text()
    vcu = (val / 'ComputerUtil.java').read_text()
    cu_tokens = [
        '"Crop Rotation".equals(ability.getHostCard().getName())',
        'ability.getApi() != ApiType.ChangeZone',
        '"Library".equals(ability.getParamOrDefault("Origin", ""))',
        '"Battlefield".equals(ability.getParamOrDefault("Destination", ""))',
        '!ability.getParamOrDefault("ChangeType", "").contains("Land")',
        'type != null && type.contains("Land")',
        'typeList = ComputerUtilCost.paymentChoicesWithoutTargets(typeList, ability, ai);',
        'TronCropRotationSelection.allowedSacrificeNames',
        'if (allowedNames != null)',
        'if (allowedNames.isEmpty())',
        'allowedNames.contains(c.getName())',
        'ComputerUtilCard.getWorstLand',
        'result.add(chosen)',
        'return result;',
    ]
    checks = {f'branch:{t}': t in cu and t in vcu for t in cu_tokens}
    checks['no_diagnostic_logging'] = 'TRON_CROP_' not in cu
    checks['unrelated_fallback'] = 'return sacList;' in cu
    add(rows, 'ComputerUtil', 'scoped_behavioral_equivalence', checks,
        scope='Crop Rotation guard, legal candidate handling, real chooseSacrificeType selector integration, selected return, unrelated fallback')

    pc = (prod / 'forge/ai/ComputerUtilCard.java').read_text()
    vc = (val / 'ComputerUtilCard.java').read_text()
    cpc = ''.join(pc.split())
    cvc = ''.join(vc.split())
    card_checks = {
        'battlefield_only_detection': 'getCardsIn(ZoneType.Battlefield)' in pc and 'getCardsIn(ZoneType.Battlefield)' in vc,
        'non_urza_fallback': '!c.getName().startsWith("Urza\'s")' in pc and '!card.getName().startsWith("Urza\'s")' in vc,
        'duplicate_detection_and_bonus': 'same>1' in cpc and 'score+=50' in cpc and 'sameNameCount>1' in cvc and 'score+=50' in cvc,
        'scarce_green_protection': 'gs<=1' in cpc and 'score-=1000' in cpc and 'greenSources<=1' in cvc and 'score-=1000' in cvc,
        'complete_tron_unique_protection': 'tron=mine&&tower&&plant' in cpc and 'tronComplete' in vc,
        'exclude_hunting_discard': 'Hunting Pack' not in pc,
        'exclude_prismatic_discard': 'Prismatic Strands' not in pc,
    }
    pieces = [
        ("Urza's Mine", 'mine', 'Mine'),
        ("Urza's Tower", 'tower', 'Tower'),
        ("Urza's Power Plant", 'plant', 'PP'),
    ]
    for piece, pv, vv in pieces:
        card_checks[f'{piece}:missing_and_available'] = (
            f'if (!{pv} && IterableUtil.any(list, CardPredicates.nameEquals("{piece}")))' in pc
            and f'if (!field{vv} && IterableUtil.any(list, (Predicate)CardPredicates.nameEquals("{piece}")))' in vc
        )
    add(rows, 'ComputerUtilCard', 'scoped_behavioral_equivalence', card_checks,
        scope='battlefield-only Tron state, missing-piece availability/ranking, duplicate/non-Urza fallback, scarce-green and unique-Tron land valuation',
        excluded=['Hunting Pack discard valuation', 'Prismatic Strands discard valuation'])

    pp = (prod / 'forge/ai/ability/PermanentAi.java').read_text()
    vp = (val / 'PermanentAi.java').read_text()
    perm_tokens = [
        'PhaseType.MAIN1', 'isPlayerTurn(ai)', '!sa.hasParam("WithoutManaCost")',
        '"Chromatic Star".equals(name)', '"Chromatic Sphere".equals(name)',
        'card.isArtifact()', '!card.getManaAbilities().isEmpty()',
        'ComputerUtil.castPermanentInMain1(ai, sa)',
    ]
    perm_checks = {f'branch:{t}': t in pp and t in vp for t in perm_tokens}
    perm_checks.update({
        'tinder_wall_removed_only_from_production': '"Tinder Wall"' not in pp and '"Tinder Wall"' in vp,
        'production_core_returns_true': 'return true;' in pp,
        'validated_core_returns_true': 'return true;' in vp,
        'production_normal_fallback': 'return !ph.is(PhaseType.MAIN1)' in pp,
    })
    add(rows, 'PermanentAi', 'scoped_behavioral_equivalence', perm_checks,
        scope='Star/Sphere/general mana-artifact MAIN1 deployment and normal fallback', excluded=['Tinder Wall'])

    stock = a.stock_changezone.read_text()
    vz = (val / 'ChangeZoneAi.java').read_text()
    add(rows, 'ChangeZoneAi', 'stock_plumbing_equivalence', {
        'production_not_generated': not (prod / 'forge/ai/ability/ChangeZoneAi.java').exists(),
        'stock_delegates_to_computer_util_card': 'ComputerUtilCard.getBestAI' in stock,
        'validated_delegates_to_computer_util_card': 'ComputerUtilCard.getBestAI' in vz,
        'stock_has_no_phase4_fetch_telemetry': 'TRON_CROP_FETCH' not in stock,
    }, scope='stock search plumbing delegates land ranking through ComputerUtilCard; diagnostic fetch telemetry excluded')

    ok = all(r['equivalent'] for r in rows)
    report = {
        'equivalent': ok,
        'standard': {
            'exact': ['TronCropRotationSelection', 'TronCropRotationSelectionTest', 'ComputerUtilMana numeric-map repair source'],
            'scoped': ['ComputerUtil', 'ComputerUtilCard', 'PermanentAi', 'ChangeZoneAi'],
        },
        'components': rows,
    }
    a.output.write_text(json.dumps(report, indent=2) + '\n')
    if not ok:
        for r in rows:
            if not r['equivalent']:
                print(r['component'], {k: v for k, v in r['checks'].items() if not v})
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
