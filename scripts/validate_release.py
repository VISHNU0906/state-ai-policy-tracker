"""Check published table relationships and dashboard consistency, without network."""
import csv,hashlib,json
from pathlib import Path
from datetime import date
from collections import Counter
from urllib.parse import urlsplit
from pipeline import config

def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def main():
    rows=read(config.OUT/'records.csv');sources=read(config.OUT/'record_sources.csv');rejected=read(config.OUT/'rejected.csv')
    ids=[r['record_id'] for r in rows]
    assert len(ids)==len(set(ids)), 'Duplicate record ID'
    assert all(r['state'] in config.PRIORITY_STATES for r in rows)
    assert all(config.START<=date.fromisoformat(r['date'])<=config.END for r in rows)
    assert rows==sorted(rows,key=lambda r:(r['date'],r['state'],r['title']),reverse=True)
    for r in rows:
        assert all(r[k] for k in ['state','title','date','source_name','source_url','summary','category'])
        assert urlsplit(r['source_url']).scheme in ('http','https') and urlsplit(r['source_url']).hostname
    assert all(s['record_id'] in set(ids) for s in sources), 'Orphan source'
    representative=Counter(s['record_id'] for s in sources if s['is_representative']=='1')
    assert all(representative[i]==1 for i in ids), 'Missing or multiple representative sources'
    assert all(r['reason'] for r in rejected)
    site=json.loads((config.SITE/'data/records.json').read_text(encoding='utf-8'))
    assert len(site['records'])==len(rows)
    for a,b in zip(rows,site['records']):assert all(str(b[k])==v for k,v in a.items())
    assert (config.OUT/'records.csv').read_bytes()==(config.SITE/'data/records.csv').read_bytes()
    counts=Counter(r['review_status'] for r in rows)
    assert set(counts)<= {'auto','legacy_headline_screen','override_applied','llm_checked'}
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(config.OUT.glob('*.csv'))}
    report={'status':'passed','records':len(rows),'states':len(set(r['state'] for r in rows)),
            'source_reports':len(sources),'rejected_items':len(rejected),'review_status':dict(counts),
            'representative_google_redirects':sum(urlsplit(r['source_url']).hostname=='news.google.com' for r in rows),
            'source_table_google_redirects':sum(urlsplit(s['link']).hostname=='news.google.com' for s in sources),
            'sha256_csv':hashes,'checks':['unique IDs','required fields','known states','ISO date and window',
            'descending date/state/title order','valid source foreign keys','one representative per record',
            'rejection reasons','CSV/JSON equivalence','site CSV byte equality','review label vocabulary']}
    out=config.ROOT/'reports';out.mkdir(exist_ok=True)
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
