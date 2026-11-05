from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: spline-outline-grip-body (build, profile=geometry) ----
    edge_0 = scad.make_spline_redge(control_points=[[-10.0, -8.0, 0.0], [0.0, -13.0, 0.0], [10.0, -8.0, 0.0]], degree=2, knots=[0.0, 1.0], multiplicities=[3, 3])
    edge_1 = scad.make_spline_redge(control_points=[[10.0, -8.0, 0.0], [14.0, 0.0, 0.0], [10.0, 8.0, 0.0]], degree=2, knots=[0.0, 1.0], multiplicities=[3, 3])
    edge_2 = scad.make_spline_redge(control_points=[[10.0, 8.0, 0.0], [0.0, 13.0, 0.0], [-10.0, 8.0, 0.0]], degree=2, knots=[0.0, 1.0], multiplicities=[3, 3])
    edge_3 = scad.make_spline_redge(control_points=[[-10.0, 8.0, 0.0], [-14.0, 0.0, 0.0], [-10.0, -8.0, 0.0]], degree=2, knots=[0.0, 1.0], multiplicities=[3, 3])
    outline = scad.make_wire_from_edges_rwire(edges=[edge_0, edge_1, edge_2, edge_3])
    result = scad.extrude_rsolid(profile=outline, direction=(0.0, 0.0, 1.0), distance=12.0)

    # ---- feature: top-fastener-boss (add, profile=geometry) ----
    boss = scad.make_cylinder_rsolid(radius=5.0, height=5.0, bottom_face_center=(0.0, 0.0, 11.0), axis=(0.0, 0.0, 1.0))
    result = scad.union_rsolid(result, boss)

    # ---- feature: blind-boss-bore (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=2.0, height=6.0, bottom_face_center=(0.0, 0.0, 11.0), axis=(0.0, 0.0, 1.0))
    result = scad.cut_rsolid(result, bore, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Spline-bodied fastener handle')

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
