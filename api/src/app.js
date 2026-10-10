import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import multer from 'multer';
import { randomUUID } from 'node:crypto';
import { z } from 'zod';
import { authentication, manager, scope } from './auth.js';
import { Incident, UploadVersion, Audit } from './models.js';
import { python } from './python.js';

const categories=['POS and Payments','Inventory and Replenishment','Pricing and Promotions','Returns and Refunds','Vendor and Supply Chain','Product Quality and Safety','Customer Service','Other or Security'];
const key=z.enum(['employee_master','escalation_matrix','inventory','product_master','receipts','returns_quality','store_master','support_cases','vendor_master']);
const id=z.string().regex(/^[a-f0-9]{24}$/);
const validate=(schema,value)=>schema.parse(value);
export function createApp({verify,profile,callPython=python,databaseReady=()=>true,models={Incident,UploadVersion,Audit}}) {
  const app=express();
  app.disable('x-powered-by'); app.set('trust proxy', Number(process.env.TRUST_PROXY_HOPS||0));
  app.use((req,res,next)=>{req.id=randomUUID(); res.set('X-Request-Id',req.id); next();});
  app.use(helmet());
  app.use(cors({origin:(origin,cb)=>cb(null,!origin||(process.env.ALLOWED_ORIGINS||'http://localhost:3000').split(',').includes(origin))}));
  app.use(express.json({limit:'32kb'}));
  app.use(rateLimit({windowMs:60000,limit:120,standardHeaders:'draft-8',legacyHeaders:false}));
  app.get('/health',(req,res)=>res.json({status:'ok'}));
  app.get('/ready',async(req,res)=>{ if(!databaseReady()) return res.status(503).json({status:'unavailable',component:'mongodb'}); try { const health=await callPython('/ready'); if(health.data_ready===false) return res.status(503).json({status:'unavailable',component:'source_data'}); res.json({status:'ready'}); } catch {res.status(503).json({status:'unavailable',component:'python'});} });
  app.use('/api/v1',authentication({verify,profile}));
  const audit=async(req,action,resourceId,outcome='ok')=>models.Audit.create({uid:req.user.uid,requestId:req.id,action,resourceId:String(resourceId),outcome});
  app.get('/api/v1/me',(req,res)=>res.json(req.user));
  app.get('/api/v1/config', (req,res)=>res.json({categories,priorities:['P1','P2','P3','P4'],statuses:['Open','In Progress','Closed']}));
  app.get('/api/v1/services',async(req,res)=>res.json(await callPython('/ready')));
  app.post('/api/v1/incidents',rateLimit({windowMs:60000,limit:10}),async(req,res)=>{
    const body=validate(z.object({text:z.string().trim().min(5).max(5000),parentId:id.optional(),requestKey:z.uuid()}).strict(),req.body);
    const existing=await models.Incident.findOne({ownerUid:req.user.uid,requestKey:body.requestKey});
    if(existing) return res.json(existing);
    const context=[];
    if(body.parentId){let current=body.parentId; for(let n=0;n<6 && current;n++) { const parent=await models.Incident.findOne({_id:current,...scope(req.user)}); if(!parent) return res.status(404).json({error:'Case not found'}); context.unshift(parent.text); current=parent.parentId; }}
    const analysis=await callPython('/v1/analyze',{method:'POST',body:{text:body.text,context}});
    if(!analysis || !['analyzed','unavailable','insufficient_evidence','safety_refusal'].includes(analysis.status) || typeof analysis.input!=='string' || !categories.includes(analysis.category) || !['P1','P2','P3','P4'].includes(analysis.priority)) {const e=new Error('Invalid AI response'); e.status=502; throw e;}
    let result;
    try { result=await models.Incident.create({ownerUid:req.user.uid,requestKey:body.requestKey,text:analysis.input,analysis,category:analysis.category,priority:analysis.priority,parentId:body.parentId}); }
    catch(error) { if(error.code===11000) return res.json(await models.Incident.findOne({ownerUid:req.user.uid,requestKey:body.requestKey})); throw error; }
    await audit(req,'case_created',result._id); res.status(201).json(result);
  });
  const listCases=async(req,res,escalations=false)=>{
    const q=validate(z.object({status:z.enum(['Open','In Progress','Closed']).optional(),priority:z.enum(['P1','P2','P3','P4']).optional(),category:z.enum(categories).optional(),q:z.string().max(120).optional(),page:z.coerce.number().int().min(1).max(10000).default(1)}).strict(),req.query);
    const filter={...scope(req.user)};
    for(const k of ['status','priority','category']) if(q[k]) filter[k]=q[k];
    if(escalations) filter['analysis.escalation.required']=true;
    if(q.q) filter.text={$regex:q.q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),$options:'i'};
    const [items,total]=await Promise.all([models.Incident.find(filter).sort({createdAt:-1}).skip((q.page-1)*25).limit(25),models.Incident.countDocuments(filter)]);
    res.json({items,total,page:q.page,pageSize:25});
  };
  app.get('/api/v1/incidents',(req,res)=>listCases(req,res));
  app.get('/api/v1/escalations',(req,res)=>listCases(req,res,true));
  app.get('/api/v1/incidents/:id',async(req,res)=>{ const row=await models.Incident.findOne({_id:validate(id,req.params.id),...scope(req.user)}); if(!row) return res.status(404).json({error:'Case not found'}); res.json(row); });
  app.patch('/api/v1/incidents/:id',manager,async(req,res)=>{
    const body=validate(z.object({status:z.enum(['Open','In Progress','Closed'])}).strict(),req.body);
    const row=await models.Incident.findOneAndUpdate({_id:validate(id,req.params.id)},{$set:body},{new:true,runValidators:true});
    if(!row) return res.status(404).json({error:'Case not found'}); await audit(req,'case_status_changed',row._id); res.json(row);
  });
  app.get('/api/v1/dashboard',async(req,res)=>{
    const match=scope(req.user); const [total,open,priorities,categoriesResult]=await Promise.all([
      models.Incident.countDocuments(match),models.Incident.countDocuments({...match,status:{$ne:'Closed'}}),
      models.Incident.aggregate([{$match:match},{$group:{_id:'$priority',count:{$sum:1}}}]),models.Incident.aggregate([{$match:match},{$group:{_id:'$category',count:{$sum:1}}}])]);
    res.json({total,open,priorities,categories:categoriesResult,scope:req.user.role==='Manager'?'All application cases':'Your application cases'});
  });
  app.post('/api/v1/analytics',async(req,res)=>{
    const body=validate(z.object({tool:z.enum(['overview','high_priority','stock_root_cause','short_shipments','quality_trends']),store_id:z.string().regex(/^(ST|WH)\d{3}$/).optional(),sku:z.string().regex(/^SKU\d{4,8}$/).optional(),days:z.number().int().min(1).max(90).optional()}).strict(),req.body);
    res.json(await callPython('/v1/analytics',{method:'POST',body}));
  });
  app.get('/api/v1/policies',async(req,res)=>{const q=validate(z.object({q:z.string().max(150).optional(),category:z.string().max(100).optional()}).strict(),req.query);res.json(await callPython('/v1/policies?'+new URLSearchParams(q)));});
  app.get('/api/v1/policies/:filename',async(req,res)=>{const name=validate(z.string().regex(/^0[1-5]_[a-z_]+\.md$/),req.params.filename);res.json(await callPython('/v1/policies/'+encodeURIComponent(name)));});
  app.use('/api/v1/datasets',manager);
  app.get('/api/v1/datasets',async(req,res)=>res.json(await callPython('/v1/datasets',{user:req.user})));
  app.get('/api/v1/datasets/:key',async(req,res)=>res.json(await callPython('/v1/datasets/'+validate(key,req.params.key),{user:req.user})));
  const upload=multer({storage:multer.memoryStorage(),limits:{fileSize:Number(process.env.UPLOAD_MAX_BYTES||5242880),files:1,fields:0},fileFilter:(req,file,cb)=>cb(null,file.originalname.toLowerCase().endsWith('.csv'))});
  app.post('/api/v1/datasets/:key/stage',rateLimit({windowMs:60000,limit:6}),upload.single('file'),async(req,res)=>{
    const dataset=validate(key,req.params.key);
    if(!req.file) return res.status(422).json({error:'Choose one CSV file'});
    // Mongo audit store must be available before beginning a mutation.
    await audit(req,'upload_requested',dataset);
    const form=new FormData(); form.append('file',new Blob([req.file.buffer],{type:'text/csv'}),req.file.originalname);
    const data=await callPython('/v1/datasets/'+dataset+'/stage',{method:'POST',form,user:req.user});
    await models.UploadVersion.create({version:data.version,dataset,uploader:req.user.uid,checksum:data.checksum,validation:data.validation,displayName:data.display_name});
    res.status(201).json(data);
  });
  for(const action of ['activate','rollback']) app.post('/api/v1/datasets/:key/'+action,async(req,res)=>{
    const dataset=validate(key,req.params.key);
    const body=validate(z.object({version:z.string().regex(/^(original|[a-f0-9]{32})$/),expected_revision:z.number().int().nonnegative(),confirm:z.literal(true)}).strict(),req.body);
    await audit(req,action+'_requested',body.version);
    const result=await callPython('/v1/datasets/'+dataset+'/'+action,{method:'POST',body,user:req.user});
    res.json(result);
  });
  app.use((req,res)=>res.status(404).json({error:'Not found',requestId:req.id}));
  app.use((error,req,res,next)=>{ // Never log tokens, prompts, provider response bodies, or upload content.
    const status=error instanceof z.ZodError?422:error.code==='LIMIT_FILE_SIZE'?413:error.status||503;
    const message=error instanceof z.ZodError?'Invalid request fields':status===413?'Upload size limit exceeded':status<500?error.message:'Service unavailable; retry or contact your manager';
    console.error(JSON.stringify({requestId:req.id,status,code:error instanceof z.ZodError?'VALIDATION_ERROR':'REQUEST_FAILED'}));
    res.status(status).json({error:message,requestId:req.id});
  });
  return app;
}
