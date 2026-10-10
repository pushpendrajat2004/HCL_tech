export function authentication({ verify, profile }) {
  return async (req,res,next) => {
    const header=req.get('authorization') || '';
    if (!/^Bearer \S+$/.test(header)) return res.status(401).json({ error: 'Sign in required', requestId: req.id });
    let identity;
    try { identity=await verify(header.slice(7)); }
    catch { return res.status(401).json({ error:'Invalid, revoked, or expired session', requestId:req.id }); }
    try {
      const user=await profile(identity.uid);
      if (!user || !['Employee','Manager'].includes(user.role)) return res.status(403).json({error:'Account permission denied'});
      req.user={uid:identity.uid,role:user.role}; next();
    } catch { res.status(503).json({error:'Profile service unavailable',requestId:req.id}); }
  };
}
export function manager(req,res,next) { if(req.user?.role!=='Manager') return res.status(403).json({error:'Manager role required',requestId:req.id}); next(); }
export function scope(user) { return user.role==='Manager'?{}:{ownerUid:user.uid}; }
