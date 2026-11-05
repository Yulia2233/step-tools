from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: sculpted-lever-outline (build, profile=geometry) ----
    heel_lower = scad.make_spline_redge(control_points=[[-50, 0, 0], [-50, -12, 0], [-40, -20, 0], [-25, -20, 0]], degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    grip_lower = scad.make_spline_redge(control_points=[[-25, -20, 0], [4, -20, 0], [50, -12, 0], [50, 0, 0]], degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    grip_upper = scad.make_spline_redge(control_points=[[50, 0, 0], [50, 12, 0], [4, 20, 0], [-25, 20, 0]], degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    heel_upper = scad.make_spline_redge(control_points=[[-25, 20, 0], [-40, 20, 0], [-50, 12, 0], [-50, 0, 0]], degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    outline = scad.make_wire_from_edges_rwire(edges=[heel_lower, grip_lower, grip_upper, heel_upper])
    result = scad.extrude_rsolid(profile=outline, direction=(0, 0, 1), distance=14.0)

    # ---- feature: raised-clamping-hub (add, profile=geometry) ----
    boss = scad.make_cylinder_rsolid(radius=13.0, height=18.0, bottom_face_center=(-28, 0, 10), axis=(0, 0, 1))
    result = scad.union_rsolid(*[result, boss], clean=True)

    # ---- feature: blind-hub-bore (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=6.0, height=9.0, bottom_face_center=(-28, 0, 20), axis=(0, 0, 1))
    result = scad.cut_rsolid(*[result, bore], skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Spline-profile clamping lever with blind hub')

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
