import json, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'ai-service'))
from app.analytics import analyze,AnalysisRequest
from app.datasets import DatasetStore
s=DatasetStore();products,_=s.frame('product_master')
tennis=products[products['name']=='Tennis Ball Pack'].iloc[0]['sku']
report={'duplicate_inventory_store_sku_rows':int(s.frame('inventory')[0].duplicated(['store_id','sku']).sum()),'tennis_sku':tennis,
        'high_priority':analyze(AnalysisRequest(tool='high_priority')),
        'quality_trends':analyze(AnalysisRequest(tool='quality_trends')),
        'short_shipments':analyze(AnalysisRequest(tool='short_shipments')),
        'cricket_bat':analyze(AnalysisRequest(tool='stock_root_cause',store_id='ST002',sku='SKU1001')),
        'tennis':analyze(AnalysisRequest(tool='stock_root_cause',store_id='ST005',sku=tennis))}
out=root/'data/generated/verified-analytics.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'duplicate_inventory_rows':report['duplicate_inventory_store_sku_rows'],'tennis_sku':tennis,'unresolved_high_priority_24h':report['high_priority']['result']['total'],'short_shipment_receipts_30d':report['short_shipments']['result']['short_receipts'],'short_shipment_units_30d':report['short_shipments']['result']['units_short'],'quality_top':report['quality_trends']['result']['vendors'][:1],'output':str(out)},indent=2))
