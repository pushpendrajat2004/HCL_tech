"""Immutable CSV versions. One locked atomic manifest is the commit/audit record."""
import csv, hashlib, io, json, os, re, uuid
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from filelock import FileLock
from . import config
from .safety import safe_tree

SCHEMAS = json.loads((config.ROOT / 'docs/source-profile.json').read_text('utf-8'))
KEYS = {'store_master':['store_id'], 'product_master':['sku'], 'employee_master':['employee_id'], 'vendor_master':['vendor_id'], 'receipts':['receipt_id'], 'support_cases':['case_id'], 'returns_quality':['return_id'],'inventory':['store_id','sku'],'escalation_matrix':['category','trigger']}
REFS = {'store_id':('store_master','store_id'), 'nearby_store_id':('store_master','store_id'), 'sku':('product_master','sku'), 'vendor_id':('vendor_master','vendor_id'), 'employee_id':('employee_master','employee_id')}

def atomic_json(path, value):
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(value, f, indent=2, allow_nan=False); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

class DatasetStore:
    def __init__(self, source=None, root=None):
        self.source = Path(source or config.SOURCE); self.root = Path(root or config.VERSIONS)
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(self.root / 'activation.lock'), timeout=15)
    def check_key(self, key):
        if key not in SCHEMAS: raise ValueError('Unknown dataset')
    def manifest(self):
        path = self.root / 'manifest.json'
        return json.loads(path.read_text('utf-8')) if path.exists() else {'revision':0,'active':{},'events':[]}
    def snapshot(self):
        return self.manifest()
    def resolve(self, key, snapshot=None):
        self.check_key(key); snap = snapshot if snapshot is not None else self.snapshot()
        version = snap['active'].get(key, 'original')
        if version == 'original': return self.source / (key+'.csv'), version
        self.check_version(version)
        return self.root / version / 'data.csv', version
    def frame(self, key, snapshot=None):
        path, version = self.resolve(key, snapshot)
        frame = pd.read_csv(path, keep_default_na=False)
        return frame, {'file':key+'.csv','version':version,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows':len(frame)}
    def validate(self, key, raw):
        self.check_key(key); errors=[]; rows=[]; headers=[]
        if not raw or len(raw)>config.MAX_BYTES: return {'valid':False,'errors':[{'message':'Empty file or size limit exceeded'}]}, None
        try:
            text = raw.decode('utf-8-sig')
            if '\x00' in text: raise ValueError('NUL bytes are not allowed')
            reader=csv.reader(io.StringIO(text, newline=''), strict=True)
            headers=next(reader)
            expected=list(SCHEMAS[key]['columns'])
            if headers != expected: raise ValueError('Headers/order must exactly match: '+', '.join(expected))
            for line,row in enumerate(reader,2):
                if len(rows)>=config.MAX_ROWS: raise ValueError('Row limit exceeded')
                if len(row)!=len(headers): errors.append({'row':line,'message':'Malformed column count'}); continue
                if any(len(v)>4000 or (any(ord(c)<32 and c not in '\t\n\r' for c in v)) for v in row):
                    errors.append({'row':line,'message':'Cell too long or contains control characters'}); continue
                rows.append(row)
                for col,v in zip(headers,row):
                    spec=SCHEMAS[key]['columns'][col]; problem=None
                    if not v and not spec['nullable']: problem='Required field'
                    elif v:
                        try:
                            if spec['type']=='integer' and not re.fullmatch(r'\d+',v): problem='Expected nonnegative integer'
                            elif spec['type']=='number' and (not re.fullmatch(r'\d+(\.\d+)?',v) or not 0<=float(v)<=1): problem='Expected rate between 0 and 1'
                            elif spec['type'] in ('date','datetime'):
                                fmt='%Y-%m-%d' if spec['type']=='date' else '%Y-%m-%d %H:%M'
                                if datetime.strptime(v,fmt).strftime(fmt)!=v: problem='Invalid date format'
                            if 'values' in spec and v not in spec['values']: problem='Unsupported category/label'
                        except ValueError: problem='Invalid date or numeric value'
                    if problem: errors.append({'row':line,'column':col,'message':problem})
                if len(errors)>=100: break
            if not rows: errors.append({'message':'At least one data row is required'})
        except (UnicodeError, ValueError, csv.Error, StopIteration) as exc:
            errors.append({'message': str(exc) or 'Empty CSV'})
        frame=pd.DataFrame(rows, columns=headers) if headers and all(len(r)==len(headers) for r in rows) else None
        if frame is not None and key in KEYS and all(c in frame for c in KEYS[key]):
            if frame.duplicated(KEYS[key]).any(): errors.append({'message':'Duplicate primary key: '+', '.join(KEYS[key])})
        report={'valid':not errors,'errors':errors[:100],'rows':len(rows),'columns':headers,
                'formula_cells':sum(v.lstrip().startswith(('=','+','-','@')) for row in rows for v in row),
                'warnings':['Formula-like text is displayed as text and escaped on CSV export.']}
        return report,frame
    def relationship_errors(self, key, frame, snapshot):
        errors=[]
        frames={k:(frame if k==key else pd.read_csv(self.resolve(k,snapshot)[0],dtype=str,keep_default_na=False)) for k in SCHEMAS}
        for dataset,df in frames.items():
            for col,(target,target_col) in REFS.items():
                if col not in df or (dataset==target and col==target_col): continue
                valid=set(frames[target][target_col].astype(str))
                bad=~df[col].astype(str).isin(valid|{''})
                if bad.any(): errors.append({'column':col,'dataset':dataset,'message':f'{int(bad.sum())} unknown references to {target}'})
        return errors
    def stage(self, key, raw, actor, display_name):
        self.check_key(key)
        report, frame=self.validate(key,raw)
        snap=self.snapshot()
        if report['valid']:
            report['errors'] += self.relationship_errors(key,frame,snap)
            report['valid']=not report['errors']
        version=uuid.uuid4().hex; folder=self.root/version
        with self.lock:
            stored=sum(p.stat().st_size for p in self.root.glob('*/data.csv'))
            if stored+len(raw)>int(os.getenv('UPLOAD_TOTAL_BYTES','1073741824')): raise ValueError('Version storage quota reached; contact the administrator for archival/backup planning')
            folder.mkdir(); (folder/'data.csv').write_bytes(raw)
        current,_=self.frame(key,snap)
        preview=frame.head(8).to_dict('records') if report['valid'] else []
        if key=='employee_master':
            for row in preview: row['employee_name']='[RESTRICTED]'
        meta={'version':version,'dataset':key,'uploader':actor,'created_at':datetime.now(timezone.utc).isoformat(),
              'display_name':re.sub(r'[^\w .-]','_',display_name)[:100], 'checksum':hashlib.sha256(raw).hexdigest(),
              'validation':report,'preview':safe_tree(preview),'comparison':{'active_rows':len(current),'staged_rows':report.get('rows',0),'row_delta':report.get('rows',0)-len(current),'columns_changed':list(current.columns)!=report.get('columns')}, 'staged_revision':snap['revision']}
        atomic_json(folder/'metadata.json',meta)
        return {**meta,'revision':snap['revision']}
    def check_version(self, version):
        if not re.fullmatch(r'[a-f0-9]{32}',version): raise ValueError('Invalid version')
    def metadata(self, version):
        self.check_version(version)
        path=self.root/version/'metadata.json'
        if not path.is_file(): raise ValueError('Version not found')
        return json.loads(path.read_text('utf-8'))
    def activate(self,key,version,actor,expected_revision,rollback=False):
        self.check_key(key)
        with self.lock:
            snap=self.snapshot()
            if snap['revision'] != expected_revision: raise ValueError('Dataset state changed; refresh preview and retry')
            if version=='original':
                if not rollback: raise ValueError('Original is a rollback target only')
                raw=(self.source/(key+'.csv')).read_bytes()
            else:
                meta=self.metadata(version)
                if meta['dataset']!=key or not meta['validation']['valid']: raise ValueError('Version is invalid for this dataset')
                raw=(self.root/version/'data.csv').read_bytes()
                if hashlib.sha256(raw).hexdigest()!=meta['checksum']: raise ValueError('Version checksum mismatch')
            report,frame=self.validate(key,raw)
            if not report['valid']: raise ValueError('Validation failed on activation')
            errors=self.relationship_errors(key,frame,snap)
            if errors: raise ValueError('Active dataset relationships would be invalid: '+json.dumps(errors))
            before=snap['active'].get(key,'original')
            snap['active'][key]=version; snap['revision']+=1
            snap['events'].append({'dataset':key,'from':before,'to':version,'actor':actor,'action':'rollback' if rollback else 'activate','at':datetime.now(timezone.utc).isoformat(),'revision':snap['revision']})
            atomic_json(self.root/'manifest.json',snap)
            return {'active_version':version,'revision':snap['revision'],'event':snap['events'][-1]}
    def history(self,key):
        self.check_key(key); snap=self.snapshot()
        versions=[json.loads(p.read_text('utf-8')) for p in self.root.glob('*/metadata.json')]
        return {'dataset':key,'revision':snap['revision'],'active_version':snap['active'].get(key,'original'),
                'versions':sorted([v for v in versions if v['dataset']==key],key=lambda v:v['created_at'],reverse=True),
                'events':[e for e in snap['events'] if e['dataset']==key]}
