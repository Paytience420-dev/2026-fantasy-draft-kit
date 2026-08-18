#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone
import json, re

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/boris-live.json'
ENDPOINTS={'QB':'https://s3-us-west-1.amazonaws.com/fftiers/out/text_QB.txt','RB':'https://s3-us-west-1.amazonaws.com/fftiers/out/text_RB-PPR.txt','WR':'https://s3-us-west-1.amazonaws.com/fftiers/out/text_WR-PPR.txt','TE':'https://s3-us-west-1.amazonaws.com/fftiers/out/text_TE-PPR.txt','FLEX':'https://s3-us-west-1.amazonaws.com/fftiers/out/text_FLX-PPR.txt'}

def get(url):
    req=Request(url,headers={'User-Agent':'Mozilla/5.0 FantasyDraftKitUpdater/1.0'})
    with urlopen(req,timeout=30) as r:return r.read().decode('utf-8','replace')

def parse(raw,pos):
    rows=[]; tier=None; rank=0
    for line in raw.splitlines():
        line=line.strip()
        if not line:continue
        m=re.search(r'Tier\s*(\d+)',line,re.I)
        if m:tier=int(m.group(1));continue
        cleaned=re.sub(r'^\s*\d+[.)-]?\s*','',line).strip()
        if tier and cleaned and len(cleaned)<80 and not cleaned.lower().startswith(('rank','player')):
            rank+=1;rows.append({'name':cleaned,'pos':pos,'tier':tier,'positionRank':rank})
    return rows

payload={'generatedAt':datetime.now(timezone.utc).isoformat(),'source':'Boris Chen public PPR text feeds','positions':{},'errors':{}}
for pos,url in ENDPOINTS.items():
    try:payload['positions'][pos]=parse(get(url),pos)
    except Exception as e:payload['errors'][pos]=str(e)
OUT.write_text(json.dumps(payload,indent=2))
print('Updated Boris public feeds')
