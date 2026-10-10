export async function python(path,{method='GET',body,user,form}={}) {
  const headers={'X-Service-Secret':process.env.INTERNAL_SERVICE_SECRET||''};
  if(user){ headers['X-Actor-Uid']=user.uid; headers['X-Actor-Role']=user.role; }
  if(body) headers['Content-Type']='application/json';
  let response;
  try { response=await fetch((process.env.PYTHON_URL||'http://127.0.0.1:8000')+path,{method,headers,body:form|| (body?JSON.stringify(body):undefined),signal:AbortSignal.timeout(Number(process.env.REQUEST_TIMEOUT_MS||180000))}); }
  catch { const e=new Error('AI/data service unavailable'); e.status=503; throw e; }
  const data=await response.json();
  if(!response.ok){ const e=new Error(typeof data.error==='string'?data.error:typeof data.detail==='string'?data.detail:'Data request rejected'); e.status=response.status; throw e; }
  return data;
}
