#!/usr/bin/env python3
from pathlib import Path
import argparse, json

ap = argparse.ArgumentParser()
ap.add_argument('--scenarios', required=True, type=Path)
ap.add_argument('--ab-dir', required=True, type=Path)
ap.add_argument('--output', required=True, type=Path)
a = ap.parse_args()
sc = json.loads(a.scenarios.read_text())
failures = json.loads((a.ab_dir / 'exceptions-timeouts.json').read_text())
perf = json.loads((a.ab_dir / 'directional-performance.json').read_text())
events = json.loads((a.ab_dir / 'behavioral-events.json').read_text())['comparison']
scenario = {x['scenario']: x for x in sc['scenarios']}

def sp(name): return scenario.get(name, {}).get('pass', False)
def ev(deck, event, build):
    for x in events:
        if x['deck']==deck and x['event']==event: return x[build]
    return 0

def p(deck, build):
    for x in perf:
        if x['deck']==deck and x['build']==build: return x
    return None

byte_ok = sp('Byte/Integer numeric mana path') and not any('ClassCastException' in json.dumps(x) for x in failures)
combo_ok = sp('Hunting Storm setup/payoff sequence') and sp('Hunting Storm win-condition recognition') and ev('hunting','hunting_pack','patched') > 0
preserve_ok = sp('Hunting Storm combo-resource preservation')
filter_ok = sp('Hunting Storm available mana-filter activation')
runtime_ok = len(failures) == 0

lines = [
'# Experimental Forge AI validation report', '',
'## Scope',
'- Recovered source: exact final PR #2 blobs; no deck changes.',
'- Stock control: Forge 2.0.14, same deck files/settings/seeds as patched build.',
'- A/B stage: 3 target decks × 3 opponents × 2 orientations × 8 games × 2 builds = 288 games.',
'- Every A/B game is verbose and stored separately; win rate is directional context only.', '',
'## Automated gates',
f"- Functional scenarios: {'PASS' if all(x['pass'] for x in sc['scenarios']) else 'FAIL'}",
f"- Runtime safety: {'PASS' if runtime_ok else 'FAIL'}",
f"- Byte/Integer exercised path: {'PASS' if byte_ok else 'FAIL'}",
f"- Unparsed/timeout/illegal/exception gate: {'PASS' if runtime_ok else 'FAIL'}", '',
'## Required questions',
f"1. **Was the prior Byte/Integer crash resolved?** {'PASS in the exercised fixed-seed mana-filter path.' if byte_ok else 'NO — the exercised path did not clear the required gate.'}",
f"2. **Does Hunting Storm now recognize and execute its combo?** {'The fixed-seed scenario and patched logs demonstrate a Hunting Pack attempt.' if combo_ok else 'NO — executable combo behavior was not demonstrated.'} Full sequencing still requires human verbose-log review.",
f"3. **Does it preserve required setup resources?** {'The fixed-seed discard scenario demonstrated preservation.' if preserve_ok else 'NO — preservation was not demonstrated in a reached discard state.'}",
f"4. **Does it use mana filters correctly?** {'A real patched Forge decision path activated a Star/Sphere filter without the prior cast failure.' if filter_ok else 'NO — the required filter decision path was not demonstrated.'}",
"5. **Does Tron use its mana engine more effectively?** Automated counters and directional results are insufficient by themselves; answer remains **pending human verbose-log comparison**.",
"6. **Does Esper make materially better interaction decisions?** Automated counters are insufficient by themselves; answer remains **pending human verbose-log comparison**.",
f"7. **Were any regressions observed?** {'No automated runtime/parse/illegal-action regression was detected; behavioral regression review is still required.' if runtime_ok else 'YES — one or more automated safety gates failed; see exceptions-timeouts.json.'}",
"8. **Is the evidence sufficient to justify a larger focused test?** **No automated conclusion.** Recommend a larger stage only if human review of the matched verbose logs confirms the intended paths and no behavioral regressions.",
"9. **Is the evidence sufficient to justify another 18,000-game baseline?** **No.** This initial focused validation cannot justify a new full baseline.", '',
'## Directional performance (not significance evidence)', '',
'| Build | Deck | Games | Wins | Losses | Win rate |', '|---|---|---:|---:|---:|---:|']
for x in perf:
    lines.append(f"| {x['build']} | {x['deck']} | {x['games']} | {x['wins']} | {x['losses']} | {x['win_rate']:.1%} |")
lines += ['', '## Reproduction',
'Run the GitHub Actions workflow `Experimental Forge AI Repair Validation` on branch `codex/validate-forge-ai-repairs`.',
'Exact one-game simulator form: `xvfb-run -a java -jar <stock-or-patched.jar> sim -d <deckA> <deckB> -D battlebox/decks -n 1 -c 120 -s <seed>`.',
'', '## Human-review requirement',
'This report intentionally does not convert compilation, exception-free execution, event counts, or small-sample win rate into a claim that the AI is repaired. Inspect the matched verbose logs and exact excerpts before any larger test is recommended.']
a.output.write_text('\n'.join(lines)+'\n', encoding='utf-8')
