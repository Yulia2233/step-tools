import sys, json, os, math, collections
sys.path.insert(0,"/tmp/blendval/cand_new"); os.environ["STEPIR_NDIG"]="4"
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
def one(f):
    import stepir, signal
    def h(*a): raise TimeoutError()
    signal.signal(signal.SIGALRM,h); signal.alarm(200)
    try:
        stepir.build_ir(f); infos=stepir.build_ir.last_infos; live=stepir.build_ir.last_live
    except BaseException: return f,[]
    rep=lambda q: infos[q].get("dead",q)
    out=[]
    ctol=math.cos(math.radians(1.0))
    for k in live:
        c=infos[k]
        if c["name"]!="CONE": continue
        nb={rep(q) for q in c["adj"]}-{k}; d=np.asarray(c["dirv"],float); d/=np.linalg.norm(d)
        planes=[g for g in nb if infos[g]["name"]=="PLANE" and abs(float(infos[g]["n"]@d))>=ctol]
        cyls=[g for g in nb if infos[g]["name"]=="CYL" and abs(float(np.asarray(infos[g]["dirv"],float)@d)/np.linalg.norm(infos[g]["dirv"]))>=ctol]
        if not (planes and cyls): continue
        vr=c["vr"]; ext=abs(vr[1]-vr[0])*math.sin(c["ang"]); rc=min(abs(float(infos[g]["rad"])) for g in cyls)
        out.append((ext/rc, ext, math.degrees(c["ang"])))
    return f,out
if __name__=="__main__":
    files=json.load(open("/tmp/blendval/files.json"))
    with ProcessPoolExecutor(8,mp_context=mp.get_context("spawn")) as ex: res=list(ex.map(one,files,chunksize=1))
    for exp in ("chamfer","fillet"):
        r=[x[0] for f,o in res if "_"+exp+"_" in f for x in o]
        print(exp,"labelled parts: cones with plane+coaxial cylinder:",len(r),"ratio quantiles 10/25/50/75/90:",np.quantile(r,[.1,.25,.5,.75,.9]).round(2).tolist() if r else None)
        print("   fraction with ratio <= 0.2:",round(float(np.mean(np.array(r)<=0.2)),2),"<=0.5:",round(float(np.mean(np.array(r)<=0.5)),2),"<=1.0:",round(float(np.mean(np.array(r)<=1.0)),2))
