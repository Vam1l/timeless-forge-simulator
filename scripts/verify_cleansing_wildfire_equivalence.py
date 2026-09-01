#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

TELEMETRY_CALL = re.compile(r'^\s*logCleansingWildfireTelemetry\([^;]+;\s*$', re.M)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def method(text: str, signature: str) -> str:
    start = text.find(signature)
    if start < 0:
        raise ValueError(f'missing method: {signature}')
    brace = text.find('{', start)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError(f'unclosed method: {signature}')


def normalized_behavior(block: str) -> str:
    block = TELEMETRY_CALL.sub('', block)
    return '\n'.join(line.rstrip() for line in block.splitlines() if line.strip())


def insertion_block(text: str) -> str:
    anchor = 'if (isExactCleansingWildfireStructure(sa)) {'
    start = text.find(anchor)
    if start < 0:
        raise ValueError('missing Cleansing Wildfire insertion block')
    brace = text.find('{', start)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError('unclosed insertion block')


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--validated-policy', type=Path, required=True)
    p.add_argument('--production-policy', type=Path, required=True)
    p.add_argument('--validated-policy-class', type=Path, required=True)
    p.add_argument('--production-policy-class', type=Path, required=True)
    p.add_argument('--validated-decision-class', type=Path, required=True)
    p.add_argument('--production-decision-class', type=Path, required=True)
    p.add_argument('--validated-destroy', type=Path, required=True)
    p.add_argument('--production-destroy', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()

    validated = a.validated_destroy.read_text()
    production = a.production_destroy.read_text()
    signatures = [
        '    private boolean isExactCleansingWildfireStructure(final SpellAbility sa)',
        '    private Card chooseCleansingWildfireCandidate(final Player ai, final SpellAbility sa)',
    ]
    methods = {}
    all_ok = True
    for signature in signatures:
        left = normalized_behavior(method(validated, signature))
        right = normalized_behavior(method(production, signature))
        ok = left == right
        all_ok &= ok
        methods[signature.strip()] = {
            'equivalent': ok,
            'validated_sha256': hashlib.sha256(left.encode()).hexdigest(),
            'production_sha256': hashlib.sha256(right.encode()).hexdigest(),
        }

    left_insert = normalized_behavior(insertion_block(validated))
    right_insert = normalized_behavior(insertion_block(production))
    insertion_ok = left_insert == right_insert
    all_ok &= insertion_ok

    policy_source_ok = a.validated_policy.read_bytes() == a.production_policy.read_bytes()
    policy_class_ok = a.validated_policy_class.read_bytes() == a.production_policy_class.read_bytes()
    decision_class_ok = a.validated_decision_class.read_bytes() == a.production_decision_class.read_bytes()
    all_ok &= policy_source_ok and policy_class_ok and decision_class_ok

    forbidden = ['CWAI', 'CWMEASURE', 'System.identityHashCode', 'logCleansingWildfireTelemetry', 'MagicStack']
    telemetry_absent = not any(token in production for token in forbidden)
    all_ok &= telemetry_absent

    report = {
        'validated_gameplay_baseline': '4a68cef04883eb029041371d738bb004bc3a95bb',
        'policy_source_exact': policy_source_ok,
        'policy_source_validated_sha256': sha(a.validated_policy),
        'policy_source_production_sha256': sha(a.production_policy),
        'policy_compiled_class_exact': policy_class_ok,
        'policy_class_validated_sha256': sha(a.validated_policy_class),
        'policy_class_production_sha256': sha(a.production_policy_class),
        'decision_class_exact': decision_class_ok,
        'decision_class_validated_sha256': sha(a.validated_decision_class),
        'decision_class_production_sha256': sha(a.production_decision_class),
        'destroy_methods': methods,
        'target_insertion_block_equivalent': insertion_ok,
        'target_insertion_validated_sha256': hashlib.sha256(left_insert.encode()).hexdigest(),
        'target_insertion_production_sha256': hashlib.sha256(right_insert.encode()).hexdigest(),
        'telemetry_and_measurement_absent': telemetry_absent,
        'pass': all_ok,
    }
    a.output.write_text(json.dumps(report, indent=2) + '\n')
    if not all_ok:
        raise SystemExit('equivalence verification failed')


if __name__ == '__main__':
    main()
