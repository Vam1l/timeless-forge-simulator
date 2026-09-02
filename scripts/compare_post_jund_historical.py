#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
JUND='06-jund-wildfire.dck'

def find_rows(root:Path):
 c=list(root.rglob('per-game.json')); good=[]
 for p in c:
  try: rows=json.loads(p.read_text())
  except Exception: continue
  if isinstance(rows,list) and rows and 'orientation_id' in rows[0] and 'seed' in rows[0]: good.append((p,rows))
 if not good: raise SystemExit('historical per-game.json not found')
 good.sort(key=lambda x:len(x[1]),reverse=True); return good[0]

def key(r):return (int(r['orientation_id']),int(r['seed']))
def dur(r):
 try:return int(r.get('duration_ms') or 0)
 except:return 0

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--current',type=Path,required=True);ap.add_argument('--historical',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 cur=json.loads(a.current.read_text()); hp,old=find_rows(a.historical); cm={key(r):r for r in cur}; om={key(r):r for r in old}
 if len(cm)!=900 or len(om)!=900 or set(cm)!=set(om): raise SystemExit(f'matched matrix mismatch current={len(cm)} historical={len(om)}')
 non=[]; jun=[]
 for k in sorted(cm):
  n,o=cm[k],om[k]; rec={'orientation_id':k[0],'seed':k[1],'deck_a':n['deck_a'],'deck_b':n['deck_b'],'old_winner':o['winner'],'new_winner':n['winner'],'winner_changed':o['winner']!=n['winner'],'old_duration_ms':dur(o),'new_duration_ms':dur(n),'duration_delta_ms':dur(n)-dur(o),'material_duration_change':abs(dur(n)-dur(o))>=2000 or (dur(o)>0 and abs(dur(n)-dur(o))/dur(o)>=0.5)}
  (jun if JUND in (n['deck_a'],n['deck_b']) else non).append(rec)
 old_j_w=sum(r['old_winner']==JUND for r in jun); new_j_w=sum(r['new_winner']==JUND for r in jun)
 transitions={'loss_to_win':sum(r['old_winner']!=JUND and r['new_winner']==JUND for r in jun),'win_to_loss':sum(r['old_winner']==JUND and r['new_winner']!=JUND for r in jun),'unchanged_wins':sum(r['old_winner']==JUND and r['new_winner']==JUND for r in jun),'unchanged_losses':sum(r['old_winner']!=JUND and r['new_winner']!=JUND for r in jun)}
 out={'historical_source':str(hp),'matched_conditions':900,'non_jund':{'games':len(non),'identical_winners':sum(not r['winner_changed'] for r in non),'changed_winners':sum(r['winner_changed'] for r in non),'material_game_length_changes':sum(r['material_duration_change'] for r in non),'changed_winner_rows':[r for r in non if r['winner_changed']]},'jund':{'games':len(jun),'old_wins':old_j_w,'old_losses':180-old_j_w,'new_wins':new_j_w,'new_losses':180-new_j_w,'percentage_point_change':(new_j_w-old_j_w)/180*100,'transitions':transitions,'rows':jun}}
 (a.output/'matched-comparison.json').write_text(json.dumps(out,indent=2)+'\n')
 md=['# Matched historical comparison','','## Non-Jund conditions',f"- Identical winners: {out['non_jund']['identical_winners']}/720",f"- Changed winners requiring review: {out['non_jund']['changed_winners']}/720",f"- Material runtime differences: {out['non_jund']['material_game_length_changes']}/720",'','## Jund conditions',f"- Historical: {old_j_w}-{180-old_j_w}",f"- Current: {new_j_w}-{180-new_j_w}",f"- Measured change: {out['jund']['percentage_point_change']:+.1f} percentage points",f"- Loss→win: {transitions['loss_to_win']}; win→loss: {transitions['win_to_loss']}; unchanged wins: {transitions['unchanged_wins']}; unchanged losses: {transitions['unchanged_losses']}"]
 (a.output/'matched-comparison.md').write_text('\n'.join(md)+'\n')
if __name__=='__main__':main()
