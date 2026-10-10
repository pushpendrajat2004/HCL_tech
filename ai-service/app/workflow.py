import re
import pandas as pd
from .config import SOURCE
from .safety import restricted

def overrides(text,category,priority):
    t=text.lower(); approval=False
    if restricted(text): return 'Other or Security','P1',True
    risk_text=re.sub(r'\b(no|without|not) (injury|injuries|safety risk|recall|fire|smoke)\b','',t)
    general_policy=bool(re.search(r'^(what is|explain|summarize|show me) .{0,70}(policy|procedure)',t))
    if not general_policy and re.search(r'\b(injured|injury|recall|unsafe|electrical shock|smoke|fire|belt slipped)\b',risk_text): return 'Product Quality and Safety','P1',True
    if re.search(r'(all registers|store.wide|entire store)',t) and re.search(r'(down|outage|cannot|not.*(?:process|work))',t): return 'POS and Payments','P1',True
    if 'multiple registers' in t and re.search(r'(cannot process|unable to process|payment outage)',t): return 'POS and Payments','P1',True
    if 'multiple registers' in t and 'degraded' in t and not re.search(r'(cannot|unable|outage)',t): return 'POS and Payments','P2',False
    if category=='Returns and Refunds':
        amounts=re.findall(r'(?:inr|rs\.?|₹)\s*([\d,]+)',t)
        amount=max([float(a.replace(',','')) for a in amounts] or [0])
        approval=bool(re.search(r'(no.receipt|without (?:a )?receipt|override)',t)) or amount>=5000
        if approval: priority='P2'
    if re.search(r'(quarantine|vendor claim|compensation|waive)',t): approval=True
    return category,priority,approval

def decide(text,category,priority,confidence,conflict=False,approval=False):
    category,priority,forced=overrides(text,category,priority)
    matrix=pd.read_csv(SOURCE/'escalation_matrix.csv',keep_default_na=False)
    rows=matrix[(matrix.category==category)&(matrix.priority==priority)]
    route=rows.iloc[0].to_dict() if len(rows) else {}
    reasons=[]
    if priority=='P1': reasons.append('P1 requires immediate human escalation')
    if confidence<0.60: reasons.append('Uncalibrated confidence estimate below 0.60')
    if conflict: reasons.append('Policy evidence is uncertain or conflicting')
    if restricted(text): reasons.append('Restricted or suspicious request')
    if approval or forced or route.get('human_approval_required')=='Yes': reasons.append('Human approval required')
    return {'category':category,'priority':priority,'escalation':{'required':bool(reasons),'reason':'; '.join(reasons),'team':route.get('team'),'channel':route.get('channel'),'sla_minutes':int(route['sla_minutes']) if route else None,'policy_source':route.get('policy_source')}}
