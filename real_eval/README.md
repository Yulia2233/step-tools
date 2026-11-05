Scripts used for the out-of-distribution checks in stepir_geom/cand/RESULTS.md (all paths inside are absolute or /tmp sandboxes).
- eval_geom_real.py: copy of bench/eval_geom.py whose natural_pairs() exempts every pair inside a same-surface connected component (the main scorer only exempts directly adjacent pairs). Used with a /tmp sandbox: bench/data/real-NNN/{orig.step,design.json}, variants from bench/build_variants.py, cand/ = the code under test.
- blend_vs_filename_labels.py: parts from work/realpool_big (ids not in benchmark/eval sets), operation kind from the file name; counts blends found by kind.
- cone_ratio_real.py: extent/coaxial-cylinder-radius of candidate chamfer cones on those parts (set CONE_EDGE_BREAK).
- g2_threshold_sweep.py: normal-angle threshold vs same-parent / cross-parent merges of free-form pairs.
Real-part sets: seed 5 (first 120, used while debugging) and seed 12 (disjoint, evaluated once). Source: work/abc_new/pool.
