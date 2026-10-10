"""Inspect every supplied row, profile schemas and verify original byte hashes."""
import csv, hashlib, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / 'docs/source-integrity.json').read_text('utf-8-sig'))
for name, digest in manifest.items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
profiles = {}
for path in sorted((ROOT / 'data').glob('*.csv')):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f); rows = list(reader); cols = reader.fieldnames
    profile = {'rows': len(rows), 'columns': {}, 'sha256': manifest['data/' + path.name]}
    for col in cols:
        vals = [r[col] for r in rows]; present = [v for v in vals if v]
        kind = 'text'
        if all(re.fullmatch(r'\d+', v) for v in present): kind = 'integer'
        elif all(re.fullmatch(r'\d+(\.\d+)?', v) for v in present): kind = 'number'
        elif all(re.fullmatch(r'\d{4}-\d{2}-\d{2}', v) for v in present): kind = 'date'
        elif all(re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', v) for v in present): kind = 'datetime'
        profile['columns'][col] = {'type': kind, 'nullable': len(present) < len(vals), 'missing': len(vals)-len(present), 'distinct': len(set(vals))}
        if col in {'role','category_label','priority_label','status','region','storage_type','high_demand','receipt_present','quality_check_ok','human_approval_required','category','primary_category'}:
            profile['columns'][col]['values'] = sorted(set(present))
    profiles[path.stem] = profile
(ROOT / 'docs/source-profile.json').write_text(json.dumps(profiles, indent=2), encoding='utf-8')
print(json.dumps({k: {'rows': v['rows'], 'columns': v['columns']} for k,v in profiles.items()}, indent=2))
print(f'Integrity verified: {len(manifest)} original files unchanged')
