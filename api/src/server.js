import 'dotenv/config';
import dotenv from 'dotenv';
import mongoose from 'mongoose';
import { initializeApp, applicationDefault } from 'firebase-admin/app';
import { getAuth } from 'firebase-admin/auth';
import { createApp } from './app.js';
import { Profile, initializeModels } from './models.js';
dotenv.config({path:'../.env',quiet:true});
const missing=['MONGODB_URI','INTERNAL_SERVICE_SECRET','GOOGLE_CLOUD_PROJECT'].filter(k=>!process.env[k]||process.env[k].startsWith('REPLACE_'));
if(missing.length || (process.env.INTERNAL_SERVICE_SECRET||'').length<32) { console.error({missing_configuration:missing,internal_secret_minimum:32}); process.exit(1); }
if(process.env.NODE_ENV==='production' && (process.env.FIREBASE_AUTH_EMULATOR_HOST || process.env.AUTH_BYPASS)) throw new Error('Production auth bypass/emulator is forbidden');
initializeApp({credential:applicationDefault(),projectId:process.env.GOOGLE_CLOUD_PROJECT});
const app=createApp({verify:token=>getAuth().verifyIdToken(token,true),profile:uid=>Profile.findOneAndUpdate({uid},{$setOnInsert:{uid,role:'Employee'}},{upsert:true,new:true,runValidators:true}),databaseReady:()=>mongoose.connection.readyState===1});
async function connect(){for(let attempt=0;attempt<10;attempt++){try{await mongoose.connect(process.env.MONGODB_URI,{serverSelectionTimeoutMS:3000});return;}catch{console.error({component:'mongodb',status:'retrying',attempt:attempt+1});await new Promise(resolve=>setTimeout(resolve,3000));}} throw new Error('MongoDB unavailable');}
await connect();
await initializeModels();
const server=app.listen(Number(process.env.API_PORT||4000),'0.0.0.0',()=>console.log('API listening'));
process.on('SIGTERM',()=>server.close(async()=>{await mongoose.disconnect();process.exit(0);}));
