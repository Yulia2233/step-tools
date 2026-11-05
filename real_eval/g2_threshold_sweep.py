import sys, json, glob, collections
import os
R=os.environ.get("STEP_TOOLS_ROOT", ".")
sys.path.insert(0,R+"/cand"); sys.path.insert(0,R+"/bench")
import numpy as np, geomnorm, eval_geom as eg
from concurrent.futures import ProcessPoolExecutor
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.TopoDS import TopoDS
def one(case):
    out=[]
    vj=json.load(open(case+"/variants.json"))["variants"]
    for v in ("split","splitnurbs"):
        if v not in vj or "error" in vj[v]: continue
        m=eg.Model(f"{case}/{v}.step"); par={int(k):x for k,x in vj[v]["parent"].items()}; diag=m.diag()
        og=eg.Model(case+"/orig.step")
        for a in range(m.n):
            if m.geo[a]["type"]!="BSPLINE": continue
            for b in m.adj[a]:
                if b<=a or m.geo[b]["type"]!="BSPLINE": continue
                if par.get(a) is None or par.get(b) is None or og.carrier[par[a]] is not None or og.carrier[par[b]] is not None: continue
                same=par.get(a)==par.get(b)
                ea=set(m.m.describe_entity(f"face:{a}")["adjacency"]["edges"]); eb=set(m.m.describe_entity(f"face:{b}")["adjacency"]["edges"])
                fa,fb=geomnorm._face_of(m.m,a),geomnorm._face_of(m.m,b); ang=[];dh=[]
                for eid in sorted(ea&eb):
                    c=BRepAdaptor_Curve(TopoDS.Edge_s(m.m.resolve_entity(eid)[-1]))
                    for t in np.linspace(c.FirstParameter(),c.LastParameter(),7)[1:-1]:
                        q=c.Value(float(t)); pt=(q.X(),q.Y(),q.Z())
                        sa,sb=geomnorm._surface_state(fa,pt),geomnorm._surface_state(fb,pt)
                        if sa is None or sb is None: continue
                        ang.append(float(np.degrees(np.arccos(np.clip(sa[0]@sb[0],-1,1))))); dh.append(abs(sa[1]-sb[1])*diag)
                if ang: out.append((same,ang,dh))
    return out
if __name__=="__main__":
    cases=sorted(glob.glob(R+"/bench/data/case-*"))
    with ProcessPoolExecutor(8) as ex: pairs=[x for r in ex.map(one,cases) for x in r]
    print("pairs",len(pairs),"same",sum(p[0] for p in pairs))
    for th in (0.03,0.1,0.3,0.6,1.0,1.5,3.0):
        for frac in (0.6,1.0):
            tp=sum(1 for s,a,h in pairs if s and np.mean(np.array(a)<=th)>=frac); fp=sum(1 for s,a,h in pairs if (not s) and np.mean(np.array(a)<=th)>=frac)
            print(f"normal angle <= {th:4.2f} deg on >= {int(frac*100):3d}% of samples: merged same-parent {tp:3d}/{sum(p[0] for p in pairs)}  merged cross-parent (wrong) {fp}")
