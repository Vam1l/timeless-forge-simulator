#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, shutil, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('base_diag', HERE / 'build_diagnostic_jar.py')
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)


def instrument_candidates(text: str) -> str:
    marker = '        // this is the "heaviest" check, which also sets up targets, defines X, etc.\n'
    insert = r'''        boolean huntingPackVisibleForCandidate = false;
        StringBuilder huntingPackVisibleZones = new StringBuilder();
        for (ZoneType z : new ZoneType[] { ZoneType.Hand, ZoneType.Exile }) {
            for (Card c : player.getCardsIn(z)) {
                if ("Hunting Pack".equals(c.getName())) {
                    huntingPackVisibleForCandidate = true;
                    if (huntingPackVisibleZones.length() > 0) huntingPackVisibleZones.append(',');
                    huntingPackVisibleZones.append(z.name());
                }
            }
        }
        if (huntingPackVisibleForCandidate && sa != null && sa.getHostCard() != null) {
            System.out.println("HUNTING_DIAG|event=candidate_enter"
                    + "|turn=" + game.getPhaseHandler().getTurn()
                    + "|phase=" + game.getPhaseHandler().getPhase()
                    + "|active_player=" + game.getPhaseHandler().getPlayerTurn()
                    + "|candidate=" + huntingDiagClean(sa.getHostCard().getName())
                    + "|pack_visible_zones=" + huntingDiagClean(huntingPackVisibleZones)
                    + "|storm_count=" + game.getView().getStormCount());
        }

        // this is the "heaviest" check, which also sets up targets, defines X, etc.
'''
    text = base.replace_once(text, marker, insert, 'candidate entry')
    marker2 = '        AiPlayDecision canPlay = canPlaySa(sa);\n        huntingDiag("ai_evaluation", sa, canPlay.name(), "canPlaySa");\n'
    insert2 = r'''        AiPlayDecision canPlay = canPlaySa(sa);
        if (huntingPackVisibleForCandidate && sa != null && sa.getHostCard() != null) {
            System.out.println("HUNTING_DIAG|event=candidate_result"
                    + "|turn=" + game.getPhaseHandler().getTurn()
                    + "|phase=" + game.getPhaseHandler().getPhase()
                    + "|active_player=" + game.getPhaseHandler().getPlayerTurn()
                    + "|candidate=" + huntingDiagClean(sa.getHostCard().getName())
                    + "|decision=" + canPlay.name()
                    + "|storm_count=" + game.getView().getStormCount());
        }
        huntingDiag("ai_evaluation", sa, canPlay.name(), "canPlaySa");
'''
    return base.replace_once(text, marker2, insert2, 'candidate result')


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--base-jar',required=True,type=Path); ap.add_argument('--ai-controller',required=True,type=Path); ap.add_argument('--token-ai',required=True,type=Path); ap.add_argument('--output-jar',required=True,type=Path); ap.add_argument('--output-dir',required=True,type=Path)
    a=ap.parse_args()
    if base.git_blob(a.ai_controller) != base.AI_CONTROLLER_BLOB: raise RuntimeError('Forge 2.0.14 AiController source blob mismatch')
    if base.git_blob(a.token_ai) != base.TOKEN_AI_BLOB: raise RuntimeError('Recovered TokenAi source blob mismatch')
    a.output_dir.mkdir(parents=True,exist_ok=True); work=a.output_dir/'overlay-src'; shutil.rmtree(work,ignore_errors=True); (work/'forge/ai/ability').mkdir(parents=True); (work/'forge/ai').mkdir(parents=True,exist_ok=True)
    ai0=a.ai_controller.read_text(); tok0=a.token_ai.read_text(); ai=instrument_candidates(base.instrument_ai_controller(ai0)); tok=base.instrument_token_ai(tok0)
    aip=work/'forge/ai/AiController.java'; tokp=work/'forge/ai/ability/TokenAi.java'; aip.write_text(ai); tokp.write_text(tok)
    import difflib
    diff=list(difflib.unified_diff(ai0.splitlines(),ai.splitlines(),fromfile='Forge-2.0.14/AiController.java',tofile='diagnostic/AiController.java',lineterm='')) + list(difflib.unified_diff(tok0.splitlines(),tok.splitlines(),fromfile='recovered/TokenAi.java',tofile='diagnostic/TokenAi.java',lineterm=''))
    (a.output_dir/'telemetry-overlay.diff').write_text('\n'.join(diff)+'\n')
    shutil.copyfile(a.base_jar,a.output_jar); classes=a.output_dir/'classes'; classes.mkdir(exist_ok=True)
    subprocess.run(['javac','-cp',str(a.output_jar),'-d',str(classes),str(aip),str(tokp)],check=True)
    subprocess.run(['jar','uf',str(a.output_jar),'-C',str(classes),'forge/ai/AiController.class','-C',str(classes),'forge/ai/ability/TokenAi.class'],check=True)
    subprocess.run(['sha256sum',str(a.base_jar),str(a.output_jar)],check=True,stdout=(a.output_dir/'jar-sha256.txt').open('w'))
    return 0
if __name__=='__main__': raise SystemExit(main())
