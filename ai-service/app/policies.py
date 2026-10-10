import hashlib, re
from .config import KB

def slug(text): return re.sub(r'[^a-z0-9 -]','',text.lower()).replace(' ','-')
def chunks(root=None,size=1600,overlap=160):
    if not 200<=size<=6000 or not 0<=overlap<size: raise ValueError('Invalid chunk settings')
    result=[]
    for path in sorted((root or KB).glob('*.md')):
        raw=path.read_bytes(); text=raw.decode('utf-8-sig').replace('\r\n','\n'); digest=hashlib.sha256(raw).hexdigest()
        title=text.splitlines()[0].lstrip('# '); sections=re.split(r'^## (.+)$',text,flags=re.M)
        for i in range(1,len(sections),2):
            heading=sections[i].strip(); body=sections[i+1].strip(); ref=path.name+'#'+slug(heading)
            for start in range(0,len(body),size-overlap):
                excerpt=body[start:start+size]
                identifier=hashlib.sha256(f'{ref}:{digest}:{start}'.encode()).hexdigest()
                result.append({'id':identifier,'reference':ref,'filename':path.name,'title':title,'section':heading,'text':excerpt,'source_hash':digest})
                if start+size>=len(body): break
    return result

def browse(query='',category=None):
    tokens=set(re.findall(r'\w+',query.lower()))
    docs=[]
    for path in sorted(KB.glob('*.md')):
        text=path.read_text('utf-8-sig'); title=text.splitlines()[0].lstrip('# ')
        if category and path.name!=category: continue
        if tokens and not all(t in text.lower() for t in tokens): continue
        docs.append({'filename':path.name,'title':title,'description':next((s.removeprefix('Applies to: ') for s in text.splitlines() if s.startswith('Applies to:')),''),'source_hash':hashlib.sha256(path.read_bytes()).hexdigest()})
    return docs

def detail(filename):
    allowed={p.name:p for p in KB.glob('*.md')}
    if filename not in allowed: raise ValueError('Unknown policy')
    return {'filename':filename,'text':allowed[filename].read_text('utf-8-sig'),'sections':[c for c in chunks() if c['filename']==filename]}
