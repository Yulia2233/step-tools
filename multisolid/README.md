# Multi-Solid STEP Preprocessor

This package prepares a multi-solid STEP assembly for the existing STEPIR v6.3 single-solid workflow. Geometry import, solid selection, transforms, STEP output, and equivalence checks use the pinned `simplecadapi==2.2.7` runtime. It does not change the existing single-solid parser or reconstruction prompt.

## Commands

Inspect a source file and print machine-readable JSON:

```bash
python multisolid/cli.py inspect input.step
```

Split, conservatively deduplicate, and generate v6.3 IR for each unique part:

```bash
python multisolid/cli.py prepare input.step --out work/multisolid/project-001 --stepir-script /path/to/frozen-v6.3/stepir.py
```

The default subprocess interpreter is the interpreter running this command. Set `MULTISOLID_PYTHON` or pass `--python` to select a different interpreter. Pass the frozen v6.3 bundled script with `--stepir-script`, or set `MULTISOLID_STEPIR_SCRIPT`. No CAD Code checkout layout is assumed, and the existing `cand/` parser and `bundle/` sources are not modified. The output directory must not already exist.

## Output

```text
project-001/
  source/source.step
  split/instance-NNN.step
  unique/part-NNN/target.step
  unique/part-NNN/target.ir.jsonl
  unique/part-NNN/ir_version.txt
  preprocess/split-manifest.json
  preprocess/dedup-report.json
  assembly.ir.json
```

All paths inside persisted JSON are relative to the project directory. `assembly.ir.json` uses schema `step-assembly-ir-v1`; each instance records a rigid `transform_from_representative` and SimpleCADAPI `placement`. Unique targets retain their source-world coordinates, so the representative instance uses identity placement. Other occurrences preserve their source STEP location.

The 2.2.7 `import_step` adapter exposes a flattened root shape, so the source occurrence tree and component labels are explicitly reported as unavailable. The preprocessor does not infer engineering mates. It records source placements and adds each instance to `unresolved` with fallback `source_placement` for the assembly agent to assess.

## Duplicate Policy

Candidate matching is only a pruning step. A merge requires either identical canonical BREP bytes after normalization, or an empty bidirectional SimpleCADAPI symmetric difference and matching topology. Volume, bounding boxes, and vertex moments never authorize a merge by themselves.

For asymmetric solids with a distinct vertex-covariance frame, the preprocessor estimates a rigid candidate frame and verifies it geometrically. If the frame is degenerate, sign-ambiguous, or rejected by the SDK transform, it falls back to translation-only matching. Such cases remain separate unless their centered geometry passes the strict check; the dedup report records the alignment mode or failure reason. Symmetric solids and STEP files with different topological segmentation can therefore remain separate even when they may be equivalent. This is a deliberate false-negative bias.

The QL solid enumeration order defines `solid-NNN` IDs for one input hash. The source SHA256, split STEP hashes, unique target hashes, STEPIR hashes, SDK version, and preprocessing version are persisted for traceability.

## Tests

Run the deterministic synthetic split/dedup test with a SimpleCADAPI 2.2.7 environment and a frozen v6.3 bundled script:

```bash
export MULTISOLID_PYTHON=/path/to/python-with-simplecadapi-2.2.7
export MULTISOLID_STEPIR_SCRIPT=/path/to/frozen-v6.3/stepir.py
"$MULTISOLID_PYTHON" -m unittest discover -s multisolid -p 'test_*.py' -v
```

The test covers a translated duplicate, a rotated asymmetric duplicate, a distinct solid, output hashes/paths, one-solid STEP files, and v6.3 IR headers.
