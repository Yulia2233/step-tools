import sys, json, time
sys.path.insert(0, sys.argv[1])
import stepir, stepir_ops
path = sys.argv[2]
t = time.time()
L = stepir.build_ir(path)
facts = stepir_ops.analyse(path, with_fit=True, lines=L)
full = stepir_ops.augment(L, facts)
txt = "\n".join(full) + "\n"
open(sys.argv[3], "w").write(txt)
h = json.loads(L[0])
print(json.dumps({"chars": len(txt), "base_chars": len("\n".join(L)), "faces": h["counts"]["face"], "implied": h.get("implied"),
                  "relief": sum(1 for l in full if l.startswith('{"derived":"relief"')), "prism": sum(1 for l in L if '"prism":' in l),
                  "B": txt.count('["B",'), "S": txt.count('["S",'), "types": h["types"], "sec": round(time.time() - t, 1)}))
