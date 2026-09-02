#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,statistics
from pathlib import Path
JUND='06-jund-wildfire.dck'

def load_rows(root:Path):
    candidates=[]
    for p in root.rglob('per-game.json'):
        try: rows=json.loads(p.read_text())
        except Exception: continue
        if isinstance(rows,list) and len(rows)==900 and rows and 'orientation_id' in rows[0] and 'seed' in rows[0]: candidates.append((p,rows))
    if len(candidates)!=1: raise RuntimeError(f'expected exactly one 900-row historical per-game.json, found {[str(p) for p,_ in candidates]}')
    return candidates[0]

def key(r): return (int(r['orientation_id']),int(r['seed']))
def duration(r): return int(r.get('duration_ms') or 0)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--current',type=Path,required=True); ap.add_argument('--historical',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
    cur=json.loads(a.current.read_text()); hp,old=load_rows(a.historical)
    cm={key(r):r for r in cur}; om={key(r):r for r in old}
    if len(cur)!=900 or len(old)!=900 or len(cm)!=900 or len(om)!=900 or set(cm)!=set(om): raise RuntimeError(f'matched matrix mismatch current_rows={len(cur)} current_unique={len(cm)} historical_rows={len(old)} historical_unique={len(om)}')
    rows=[]
    for k in sorted(cm):
        n,o=cm[k],om[k]
        if (n['deck_a'],n['deck_b'])!=(o['deck_a'],o['deck_b']): raise RuntimeError(f'orientation deck identity mismatch at {k}')
        dd=duration(n)-duration(o)
        rows.append({'orientation_id':k[0],'pair_id':int(n['pair_id']),'seed':k[1],'deck_a':n['deck_a'],'deck_b':n['deck_b'],'old_winner':o['winner'],'new_winner':n['winner'],'winner_changed':o['winner']!=n['winner'],'old_turns':int(o.get('turns') or 0),'new_turns':int(n.get('turns') or 0),'old_duration_ms':duration(o),'new_duration_ms':duration(n),'duration_delta_ms':dd,'material_duration_change':abs(dd)>=2000 or (duration(o)>0 and abs(dd)/duration(o)>=.5)})
    j=[r for r in rows if JUND in (r['deck_a'],r['deck_b'])]; non=[r for r in rows if JUND not in (r['deck_a'],r['deck_b'])]
    if len(j)!=180 or len(non)!=720: raise RuntimeError(f'partition mismatch jund={len(j)} non_jund={len(non)}')
    oldw=sum(r['old_winner']==JUND for r in j); neww=sum(r['new_winner']==JUND for r in j)
    trans={'loss_to_win':sum(r['old_winner']!=JUND and r['new_winner']==JUND for r in j),'win_to_loss':sum(r['old_winner']==JUND and r['new_winner']!=JUND for r in j),'unchanged_wins':sum(r['old_winner']==JUND and r['new_winner']==JUND for r in j),'unchanged_losses':sum(r['old_winner']!=JUND and r['new_winner']!=JUND for r in j)}
    per_matchup=[]
    opponents=sorted({r['deck_b'] if r['deck_a']==JUND else r['deck_a'] for r in j})
    for opp in opponents:
        rr=[r for r in j if opp in (r['deck_a'],r['deck_b'])]
        per_matchup.append({'opponent':opp,'games':len(rr),'old_jund_wins':sum(r['old_winner']==JUND for r in rr),'new_jund_wins':sum(r['new_winner']==JUND for r in rr),'loss_to_win':sum(r['old_winner']!=JUND and r['new_winner']==JUND for r in rr),'win_to_loss':sum(r['old_winner']==JUND and r['new_winner']!=JUND for r in rr)})
    orientation=[]
    for seat in ('first','second'):
        rr=[r for r in j if (r['deck_a']==JUND)==(seat=='first')]
        orientation.append({'jund_seat':seat,'games':len(rr),'old_wins':sum(r['old_winner']==JUND for r in rr),'new_wins':sum(r['new_winner']==JUND for r in rr)})
    out={'historical_source':str(hp),'matched_conditions':900,'non_jund':{'games':720,'identical_winners':sum(not r['winner_changed'] for r in non),'changed_winners':sum(r['winner_changed'] for r in non),'material_game_length_changes':sum(r['material_duration_change'] for r in non),'changed_winner_rows':[r for r in non if r['winner_changed']]},'jund':{'games':180,'old_wins':oldw,'old_losses':180-oldw,'new_wins':neww,'new_losses':180-neww,'percentage_point_change':(neww-oldw)/180*100,'transitions':trans,'per_matchup':per_matchup,'orientation':orientation,'median_duration_delta_ms':statistics.median([r['duration_delta_ms'] for r in j]),'rows':j}}
    (a.output/'matched-comparison.json').write_text(json.dumps(out,indent=2)+'\n')
    md=['# Matched pre/post-Jund comparison','',f"Historical source: `{hp}`",'', '## Non-Jund 720-game partition',f"- Identical winners: {out['non_jund']['identical_winners']}/720",f"- Changed winners: {out['non_jund']['changed_winners']}/720",f"- Material game-length changes: {out['non_jund']['material_game_length_changes']}/720",'', '## Jund 180-game partition',f"- Historical Jund: {oldw}-{180-oldw}",f"- Current Jund: {neww}-{180-neww}",f"- Measured effect: {out['jund']['percentage_point_change']:+.1f} percentage points",f"- Loss→win {trans['loss_to_win']}; win→loss {trans['win_to_loss']}; unchanged wins {trans['unchanged_wins']}; unchanged losses {trans['unchanged_losses']}"]
    (a.output/'matched-comparison.md').write_text('\n'.join(md)+'\n')
if __name__=='__main__': main()
