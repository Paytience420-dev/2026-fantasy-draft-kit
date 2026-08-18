#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone
import hashlib, json

ROOT=Path(__file__).resolve().parents[1]
SOURCES=json.loads((ROOT/'data/sources.json').read_text())
OUT=ROOT/'data/source-audit.json'
previous={}
if OUT.exists():
    try: previous={x['id']:x for x in json.loads(OUT.read_text()).get('sources',[])}
    except Exception: previous={}

def fetch(url:str):
    req=Request(url,headers={'User-Agent':'Mozilla/5.0 FantasyDraftKitAudit/1.0'})
    with urlopen(req,timeout=30) as r:
        body=r.read()
        return {'httpStatus':getattr(r,'status',200),'finalUrl':r.geturl(),'etag':r.headers.get('ETag'),'lastModified':r.headers.get('Last-Modified'),'contentHash':hashlib.sha256(body).hexdigest(),'bytes':len(body)}

rows=[]
for source in SOURCES:
    row=dict(source); old=previous.get(source['id'],{})
    if not source.get('url'):
        row.update(auditStatus='manual-review',auditMessage='Manual screenshot or embedded source; no public URL to poll.',changeDetected=False)
    else:
        try:
            info=fetch(source['url']); changed=bool(old.get('contentHash') and old.get('contentHash')!=info['contentHash'])
            row.update(info,auditStatus='ready' if source.get('weight',0)>0 or source['id'] in {'draftsharks','google-sheet'} else 'manual-review',auditMessage='Public URL reachable.',changeDetected=changed)
        except HTTPError as e:
            row.update(httpStatus=e.code,auditStatus='blocked',auditMessage=f'HTTP {e.code}',changeDetected=False)
        except (URLError,TimeoutError,Exception) as e:
            row.update(auditStatus='blocked',auditMessage=str(e)[:180],changeDetected=False)
    row['lastChecked']=datetime.now(timezone.utc).isoformat(); rows.append(row)
OUT.write_text(json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),'summary':{'sources':len(rows),'changed':sum(bool(x.get('changeDetected')) for x in rows),'ready':sum(x.get('auditStatus')=='ready' for x in rows),'blocked':sum(x.get('auditStatus')=='blocked' for x in rows)},'sources':rows},indent=2))
print(f'Audited {len(rows)} sources')
