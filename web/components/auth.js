'use client';
import { createContext,useContext,useEffect,useState } from 'react';
import { initializeApp,getApps } from 'firebase/app';
import { getAuth,onAuthStateChanged,signOut } from 'firebase/auth';
const Context=createContext(null);
export function firebaseAuth(){
  const config={apiKey:process.env.NEXT_PUBLIC_FIREBASE_API_KEY,authDomain:process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,projectId:process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,appId:process.env.NEXT_PUBLIC_FIREBASE_APP_ID};
  if(Object.values(config).some(v=>!v||v.startsWith('REPLACE_'))) throw new Error('Firebase sign-in is not configured. Add the public Firebase settings and rebuild the web app.');
  return getAuth(getApps()[0]||initializeApp(config));
}
export const API=process.env.NEXT_PUBLIC_API_URL||'http://localhost:4000/api/v1';
export async function api(path,options={}){
  const user=firebaseAuth().currentUser;
  if(!user) throw new Error('Sign in to continue.');
  const token=await user.getIdToken();
  const response=await fetch(API+path,{...options,headers:{Authorization:'Bearer '+token,...(options.body?{'Content-Type':'application/json'}:{}),...options.headers},signal:options.signal||AbortSignal.timeout(180000)});
  const data=await response.json();
  if(!response.ok) throw new Error(data.error||'The service is unavailable. Please retry.');
  return data;
}
export function AuthProvider({children}){
  const [state,setState]=useState({user:null,profile:null,loading:true,error:''});
  useEffect(()=>{let active=true; let unsubscribe;
    try{unsubscribe=onAuthStateChanged(firebaseAuth(),async user=>{
      if(!active)return;
      if(!user){setState({user:null,profile:null,loading:false,error:''});return;}
      setState({user,profile:null,loading:true,error:''});
      try{const profile=await api('/me');if(active)setState({user,profile,loading:false,error:''});}
      catch(e){if(active)setState({user,profile:null,loading:false,error:e.message});}
    });}catch(e){setState({user:null,profile:null,loading:false,error:e.message});}
    return()=>{active=false;unsubscribe?.();};
  },[]);
  return <Context.Provider value={{...state,logout:()=>signOut(firebaseAuth())}}>{children}</Context.Provider>;
}
export function useAuth(){return useContext(Context);}
