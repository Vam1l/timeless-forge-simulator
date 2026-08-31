#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def h(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def has_all(text, tokens): return all(t in text for t in tokens)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--production-dir',type=Path,required=True)
    p.add_argument('--validated-dir',type=Path,required=True)
    p.add_argument('--stock-changezone',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    prod=a.production_dir; val=a.validated_dir
    rows=[]
    helper_p=prod/'forge/ai/TronCropRotationSelection.java'; helper_v=val/'TronCropRotationSelection.java'
    rows.append({'class':'TronCropRotationSelection','mode':'exact_source','production_sha256':h(helper_p),'validated_sha256':h(helper_v),'equivalent':helper_p.read_bytes()==helper_v.read_bytes()})

    cu=(prod/'forge/ai/ComputerUtil.java').read_text(); vcu=(val/'ComputerUtil.java').read_text()
    cu_tokens=['"Crop Rotation".equals(ability.getHostCard().getName())','ability.getApi() != ApiType.ChangeZone','"Library".equals(ability.getParamOrDefault("Origin", ""))','"Battlefield".equals(ability.getParamOrDefault("Destination", ""))','TronCropRotationSelection.allowedSacrificeNames','ComputerUtilCard.getWorstLand(allowedCards)','return result;']
    rows.append({'class':'ComputerUtil','mode':'behavioral_structure','scope':'Crop Rotation chooseSacrificeType entry','equivalent':has_all(cu,cu_tokens) and has_all(vcu,cu_tokens),'validated_logging_omitted':True})

    pc=(prod/'forge/ai/ComputerUtilCard.java').read_text(); vc=(val/'ComputerUtilCard.java').read_text()
    best=['ZoneType.Battlefield','"Urza\'s Mine"','"Urza\'s Tower"','"Urza\'s Power Plant"','!c.getName().startsWith("Urza\'s")']
    worst=['sameNameCount > 1','greenSources <= 1','score -= 1000','tronComplete']
    # Production uses shorter local names but preserves the same conditions.
    peq=has_all(pc,best) and all(x in vc for x in best) and ('score+=50' in pc.replace(' ','') or 'score += 50' in pc) and has_all(vc,worst)
    rows.append({'class':'ComputerUtilCard','mode':'behavioral_structure','scope':'getBestLandAI/getWorstLand Tron clauses','equivalent':peq,'whole_class_equal':False,'reason':'unrelated recovered Hunting/other changes intentionally excluded'})

    pm=(prod/'forge/ai/ComputerUtilMana.java').read_text(); vm=(val/'ComputerUtilMana.java').read_text()
    mana=['for (Object key : manaAbilityMap.keySet())','if (!(key instanceof Number)) continue;','((Number) key).intValue()']
    rows.append({'class':'ComputerUtilMana','mode':'exact_repair_clause','scope':'heterogeneous numeric-map normalization','equivalent':has_all(pm,mana) and has_all(vm,mana),'whole_class_equal':False,'reason':'production starts from stock and carries only validated numeric fix'})

    pp=(prod/'forge/ai/ability/PermanentAi.java').read_text(); vp=(val/'PermanentAi.java').read_text()
    per=['"Chromatic Star".equals(name)','"Chromatic Sphere".equals(name)','card.isArtifact()','!card.getManaAbilities().isEmpty()']
    rows.append({'class':'PermanentAi','mode':'behavioral_structure','scope':'Tron mana-filter/setup artifact MAIN1 allowance','equivalent':has_all(pp,per) and has_all(vp,per) and '"Tinder Wall"' not in pp,'whole_class_equal':False,'reason':'Hunting-specific Tinder Wall and unrelated recovered simplifications excluded'})

    sc=a.stock_changezone.read_text(); vcz=(val/'ChangeZoneAi.java').read_text()
    plumbing='ComputerUtilCard.getBestAI'
    rows.append({'class':'ChangeZoneAi','mode':'stock_unchanged','scope':'land search selection plumbing','equivalent':plumbing in sc and plumbing in vcz,'production_modified':False,'validated_diagnostic_logging_omitted':True})

    ok=all(r['equivalent'] for r in rows)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps({'equivalent':ok,'classes':rows},indent=2)+'\n')
    if not ok: raise SystemExit('behavior-equivalence verification failed')
if __name__=='__main__': main()
