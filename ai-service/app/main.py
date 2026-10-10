import hmac, os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Header, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field
from . import config
from .analytics import AnalysisRequest, analyze
from .datasets import DatasetStore, SCHEMAS
from .pipeline import IncidentRequest, run
from .policies import browse, detail

def service_auth(x_service_secret:str=Header(default='')):
    expected=os.getenv('INTERNAL_SERVICE_SECRET','')
    if len(expected)<32 or expected.startswith('REPLACE_'): raise HTTPException(503,'INTERNAL_SERVICE_SECRET is missing or too short')
    if not hmac.compare_digest(x_service_secret,expected): raise HTTPException(401,'Internal authorization required')
def manager(x_actor_role:str=Header(default=''),x_actor_uid:str=Header(default='')):
    if x_actor_role!='Manager' or not x_actor_uid or len(x_actor_uid)>128: raise HTTPException(403,'Manager role required')
    return x_actor_uid
@asynccontextmanager
async def lifespan(app):
    print({'missing_ai_configuration':config.missing_ai()})
    yield
app=FastAPI(title='PSM private AI and data API',version='1.0.0',docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
@app.exception_handler(RequestValidationError)
async def invalid_request(request,exc):
    return JSONResponse(status_code=422,content={'error':'Invalid request fields','fields':[{'location':e['loc'],'type':e['type']} for e in exc.errors()]})
@app.exception_handler(ValueError)
async def value_error(request,exc): return JSONResponse(status_code=422,content={'error':str(exc)[:800]})
@app.exception_handler(Exception)
async def unknown_error(request,exc): return JSONResponse(status_code=503,content={'error':'Data/AI service unavailable'})
@app.get('/health')
def health(): return {'status':'ok'}
@app.get('/ready',dependencies=[Depends(service_auth)])
def ready():
    return {'data_ready':all((config.SOURCE/(k+'.csv')).exists() for k in SCHEMAS),'missing_ai_configuration':config.missing_ai(),'ai_configured':not config.missing_ai()}
@app.get('/openapi.json',dependencies=[Depends(service_auth)])
def openapi(): return app.openapi()
@app.post('/v1/analyze',dependencies=[Depends(service_auth)])
def incident(req:IncidentRequest): return run(req)
@app.post('/v1/analytics',dependencies=[Depends(service_auth)])
def analytics(req:AnalysisRequest): return analyze(req)
@app.get('/v1/policies',dependencies=[Depends(service_auth)])
def policies(q:str=Query(default='',max_length=150),category:str|None=Query(default=None,max_length=100)): return browse(q,category)
@app.get('/v1/policies/{filename}',dependencies=[Depends(service_auth)])
def policy(filename:str): return detail(filename)
@app.get('/v1/datasets',dependencies=[Depends(service_auth),Depends(manager)])
def datasets(): return [{'key':k,'rows':v['rows'],'columns':list(v['columns'])} for k,v in SCHEMAS.items()]
@app.get('/v1/datasets/{key}',dependencies=[Depends(service_auth),Depends(manager)])
def history(key:str): return DatasetStore().history(key)
@app.post('/v1/datasets/{key}/stage',dependencies=[Depends(service_auth)])
async def stage(key:str,actor:str=Depends(manager),file:UploadFile=File()):
    if not (file.filename or '').lower().endswith('.csv'): raise HTTPException(422,'Only CSV files are supported')
    raw=await file.read(config.MAX_BYTES+1)
    if len(raw)>config.MAX_BYTES: raise HTTPException(413,'Upload size limit exceeded')
    return DatasetStore().stage(key,raw,actor,file.filename)
class Activation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    version:str=Field(pattern=r'^(original|[a-f0-9]{32})$')
    expected_revision:int=Field(ge=0)
    confirm:bool
@app.post('/v1/datasets/{key}/{action}',dependencies=[Depends(service_auth)])
def activate(key:str,action:str,req:Activation,actor:str=Depends(manager)):
    if action not in ('activate','rollback') or not req.confirm: raise HTTPException(422,'Explicit activation/rollback confirmation required')
    return DatasetStore().activate(key,req.version,actor,req.expected_revision,action=='rollback')
