from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: swept-handle-body (build, profile=geometry) ----
    profile_wire = scad.make_circle_rwire(center=(0.0, 0.0, 0.0), radius=2.5, normal=(1.0, 0.0, 0.0))
    profile = scad.make_face_from_wire_rface(wire=profile_wire, normal=(1.0, 0.0, 0.0))
    rail_edge = scad.make_spline_redge(control_points=[[0.0, 0.0, 0.0], [5.0, 0.0, 1.5], [9.0, 2.5, 4.0], [13.0, 5.0, 7.0], [16.0, 4.0, 10.0], [19.0, 0.0, 12.5], [22.0, -3.0, 15.0]], degree=3, knots=[0.0, 0.25, 0.5, 0.75, 1.0], multiplicities=[4, 1, 1, 1, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=True)

    # ---- feature: end-rim-chamfers (modify, profile=geometry) ----
    rim_edges = scad.ql.edges().where(scad.ql.prop('geom.length', '<', 16.0)).exactly(2)
    result = scad.chamfer_rsolid(solid=result, edges=rim_edges, distance=0.35)

    return scad.make_part_rpart(part_id='part', body=result, name='Swept spline handle')

if __name__ == "__main__":
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from simplecadapi.exporter.step import export_product_package_to_step
    with TemporaryDirectory(prefix="tail-solid-export-") as scratch:
        product = build()
        package = Path(scratch) / "product.scadpkg"
        scad.capture(product, package, include_scene=False)
        export_product_package_to_step(data=package,
            output_path=Path(__file__).with_suffix(".step"))
