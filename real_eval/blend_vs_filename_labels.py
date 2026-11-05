import sys, json, os, signal, collections
cand=sys.argv[1]; out=sys.argv[2]
sys.path.insert(0,cand); os.environ["STEPIR_NDIG"]="4"
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
def one(f):
    import stepir, stepir_ops
    def h(*a): raise TimeoutError()
    signal.signal(signal.SIGALRM,h); signal.alarm(200)
    try:
        facts=stepir_ops.analyse(f)
        c=collections.Counter((b["kind"],b["carrier"]) for b in facts["blends"])
        return f,{f"{k}/{v}":n for (k,v),n in c.items()},facts["n_faces"]
    except BaseException as e:
        return f,"ERR "+type(e).__name__,0
if __name__=="__main__":
    files=json.load(open("/tmp/blendval/files.json"))
    with ProcessPoolExecutor(8,mp_context=mp.get_context("spawn")) as ex: res=list(ex.map(one,files,chunksize=1))
    json.dump(res,open(out,"w"))
    S=collections.Counter()
    for f,c,n in res:
        exp="fillet" if "_fillet_" in f else "chamfer"
        if isinstance(c,str): S[exp+" err"]+=1; continue
        S[exp+" parts"]+=1
        kinds={k.split("/")[0] for k in c}
        if exp in kinds: S[exp+" found-expected"]+=1
        if kinds-{exp}: S[exp+" found-OTHER-kind"]+=1
        if not kinds: S[exp+" nothing"]+=1
    print(dict(sorted(S.items())))
