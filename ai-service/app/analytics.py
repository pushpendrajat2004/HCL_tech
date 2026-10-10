import json
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from .config import ANCHOR
from .datasets import DatasetStore
from .safety import safe_tree

class AnalysisRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    tool: Literal['overview','high_priority','stock_root_cause','short_shipments','quality_trends']
    store_id: str|None=Field(default=None,pattern=r'^(ST\d{3}|WH\d{3})$')
    sku: str|None=Field(default=None,pattern=r'^SKU\d{4,8}$')
    days: int=Field(default=30,ge=1,le=90)

def records(frame): return json.loads(frame.to_json(orient='records'))
def window(frame, column, days):
    ts=pd.to_datetime(frame[column],format='%Y-%m-%d %H:%M').dt.tz_localize('Asia/Kolkata')
    anchor=pd.Timestamp(ANCHOR)
    return frame[(ts>=anchor-pd.Timedelta(days=days))&(ts<=anchor)]

def analyze(req:AnalysisRequest,store=None):
    store=store or DatasetStore(); snap=store.snapshot(); sources=[]
    def get(key):
        df,meta=store.frame(key,snap); sources.append(meta); return df
    def filtered(df):
        if req.store_id and 'store_id' in df: df=df[df.store_id==req.store_id]
        if req.sku and 'sku' in df: df=df[df.sku==req.sku]
        return df
    caveats=['Supplied demonstration data; no live retail-system connection.', 'Time windows use 2026-10-10 12:00 IST.']
    if req.tool in ('overview','high_priority'):
        cases=filtered(get('support_cases')); stores=get('store_master')
        if req.tool=='high_priority': cases=window(cases,'created_ts',1); cases=cases[(cases.status!='Closed')&cases.priority_label.isin(['P1','P2'])]
        result={'total':len(cases),'open':int((cases.status!='Closed').sum()),
                'by_priority':cases.priority_label.value_counts().to_dict(), 'by_category':cases.category_label.value_counts().to_dict(),
                'by_region':cases.merge(stores[['store_id','region']],on='store_id').region.value_counts().to_dict(),
                'groups':records(cases.groupby(['store_id','category_label','priority_label','status']).size().reset_index(name='count'))}
    elif req.tool=='stock_root_cause':
        if not req.sku or not req.store_id: raise ValueError('Stock analysis requires store_id and sku')
        inventory=get('inventory'); products=get('product_master'); receipts=get('receipts'); vendors=get('vendor_master'); cases=get('support_cases')
        stock=filtered(inventory); product=products[products.sku==req.sku]
        recent=filtered(receipts); recent=recent[(recent.receipt_date>=str(pd.Timestamp(ANCHOR).date()-pd.Timedelta(days=req.days)))&(recent.receipt_date<='2026-10-10')]
        recent=recent.sort_values('receipt_date',ascending=False)
        nearby=inventory[(inventory.sku==req.sku)&(inventory.store_id!=req.store_id)]
        warehouse=nearby[nearby.store_id.str.startswith('WH')]
        findings=[]
        if len(stock) and (stock.on_hand==0).all() and len(warehouse) and (warehouse.on_hand==0).all(): findings.append('Store and warehouse both show zero stock; warehouse depletion is a supported likely cause.')
        if len(recent) and (recent.received_qty<recent.po_qty).any(): findings.append('Recent short shipments may contribute; investigate before assigning fault.')
        if len(stock):
            diff=(stock.system_qty-stock.on_hand).abs()
            percent=diff/stock.system_qty.clip(lower=1)
            if ((diff>10)|(percent>.20)).any(): findings.append('Quantity discrepancy exceeds ten units or twenty percent of system quantity; cycle count review is supported. A zero system quantity uses a denominator of one unit.')
        consecutive=[]
        for vendor,group in recent.groupby('vendor_id'):
            latest=group.head(2)
            if len(latest)==2 and (latest.received_qty<latest.po_qty).all(): consecutive.append(str(vendor))
        if consecutive: findings.append('The latest two receipts are short for vendor(s) '+', '.join(consecutive)+'. Vendor claim review is supported; human approval is required.')
        result={'inventory':records(stock),'product':records(product),'receipts':records(recent),'vendors':records(vendors[vendors.vendor_id.isin(product.vendor_id)]),
                'warehouse':records(warehouse),'other_stock':records(nearby[nearby.on_hand>nearby.reorder_point].head(10)),
                'related_case_count':len(filtered(cases)), 'findings':findings}
        caveats.append('Inventory is a store/SKU snapshot, not a daily stock history. Longitudinal stock-out frequency cannot be inferred from it.')
    elif req.tool=='short_shipments':
        df=filtered(get('receipts')); vendors=get('vendor_master')
        df=df[(df.receipt_date>=str(pd.Timestamp(ANCHOR).date()-pd.Timedelta(days=req.days)))&(df.receipt_date<='2026-10-10')].copy()
        df['short_qty']=(df.po_qty-df.received_qty).clip(lower=0)
        df=df[df.short_qty>0]
        result={'short_receipts':len(df),'units_short':int(df.short_qty.sum()),'by_vendor':records(df.groupby('vendor_id')[['po_qty','received_qty','short_qty']].sum().reset_index().merge(vendors[['vendor_id','name','fill_rate','on_time_rate']],on='vendor_id'))}
    else:
        products=get('product_master'); vendors=get('vendor_master')
        cases=window(filtered(get('support_cases')),'created_ts',req.days)
        returns=window(filtered(get('returns_quality')),'created_ts',req.days)
        cases=cases[cases.category_label=='Product Quality and Safety']
        # Explicit taxonomy from the actual reason column; routine exchanges are excluded.
        reasons=['Football seam split','Football lost air quickly','Treadmill belt slipped during demo','Quality complaint','Exercise bike damaged no receipt','Treadmill damaged no receipt','Damaged packaging']
        returns=returns[returns.reason.isin(reasons)]
        a=cases.merge(products[['sku','vendor_id']],on='sku').groupby('vendor_id').size().rename('support_complaints')
        b=returns.merge(products[['sku','vendor_id']],on='sku').groupby('vendor_id').size().rename('quality_returns')
        merged=pd.concat([a,b],axis=1).fillna(0).astype(int).reset_index()
        merged['record_count']=merged.support_complaints+merged.quality_returns
        result={'vendors':records(merged.merge(vendors[['vendor_id','name','fill_rate','on_time_rate']],on='vendor_id').sort_values('record_count',ascending=False)), 'quality_return_reasons':reasons}
        caveats.append('Support and return records cannot be deduplicated into unique complaints: no cross-reference key exists. Totals indicate associated records, not vendor fault.')
    return safe_tree({'tool':req.tool,'filters':req.model_dump(exclude_none=True),'anchor':ANCHOR,'revision':snap['revision'],'sources':sources,'result':result,'caveats':caveats})
