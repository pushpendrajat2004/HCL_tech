"""Explicit operator command: create a legacy vector index for BYO embeddings."""
import json, os, time
from .providers import embed, request, pinecone_headers, index_info, Unavailable
def create():
    dimension=len(embed(['embedding dimension probe'])[0])
    cloud=os.getenv('PINECONE_CLOUD');region=os.getenv('PINECONE_REGION');name=os.getenv('PINECONE_INDEX')
    if not cloud or not region or not name or region.startswith('REPLACE_'):raise Unavailable('Configure PINECONE_INDEX, PINECONE_CLOUD, PINECONE_REGION')
    request('POST','https://api.pinecone.io/indexes',headers=pinecone_headers(),json={'name':name,'dimension':dimension,'metric':os.getenv('PINECONE_METRIC','cosine'),'spec':{'serverless':{'cloud':cloud,'region':region}},'deletion_protection':'enabled'})
    for _ in range(30):
        try:return {'host':index_info(dimension),'dimension':dimension,'index':name}
        except Unavailable:time.sleep(2)
    raise Unavailable('Index readiness not verified; inspect Pinecone console before retrying')
if __name__=='__main__':
    try:print(json.dumps(create(),indent=2))
    except Unavailable as exc:print(str(exc));raise SystemExit(1)
