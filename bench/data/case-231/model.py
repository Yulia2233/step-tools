from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: noncongruent-grip-sections (build, profile=geometry) ----
    heel_edge = scad.make_spline_redge(control_points=[
        [18, 0, 0], [18, 7, 0], [10, 12, 0], [0, 12, 0],
        [-10, 12, 0], [-18, 7, 0], [-18, 0, 0],
        [-18, -7, 0], [-10, -12, 0], [0, -12, 0],
        [10, -12, 0], [18, -7, 0], [18, 0, 0]],
        degree=3, knots=[0, 1, 2, 3, 4], multiplicities=[4, 3, 3, 3, 4])
    heel = scad.make_wire_from_edges_rwire(edges=[heel_edge])
    palm_edge = scad.make_spline_redge(control_points=[
        [21, 1, 19], [21, 11, 19], [12, 16, 19], [2, 16, 19],
        [-8, 16, 19], [-15, 10, 19], [-15, 1, 19],
        [-15, -8, 19], [-8, -12, 19], [2, -12, 19],
        [12, -12, 19], [21, -9, 19], [21, 1, 19]],
        degree=3, knots=[0, 1, 2, 3, 4], multiplicities=[4, 3, 3, 3, 4])
    palm = scad.make_wire_from_edges_rwire(edges=[palm_edge])
    neck_edge = scad.make_spline_redge(control_points=[
        [16, -1, 41], [16, 5, 41], [8, 13, 41], [1, 13, 41],
        [-6, 13, 41], [-12, 7, 41], [-12, -1, 41],
        [-12, -9, 41], [-6, -11, 41], [1, -11, 41],
        [8, -11, 41], [16, -7, 41], [16, -1, 41]],
        degree=3, knots=[0, 1, 2, 3, 4], multiplicities=[4, 3, 3, 3, 4])
    neck = scad.make_wire_from_edges_rwire(edges=[neck_edge])
    nose_edge = scad.make_spline_redge(control_points=[
        [15, 0, 60], [15, 3, 60], [0, 11, 60], [-3, 11, 60],
        [-6, 11, 60], [-9, 7, 60], [-9, 0, 60],
        [-9, -7, 60], [-6, -11, 60], [-3, -11, 60],
        [0, -11, 60], [15, -3, 60], [15, 0, 60]],
        degree=3, knots=[0, 1, 2, 3, 4], multiplicities=[4, 3, 3, 3, 4])
    nose = scad.make_wire_from_edges_rwire(edges=[nose_edge])

    # ---- feature: smooth-ergonomic-sleeve (build, profile=geometry) ----
    result = scad.loft_rsolid(profiles=[heel, palm, neck, nose], ruled=False)

    # ---- feature: axial-shaft-through-bore (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=4.0, height=64.0, bottom_face_center=(0, 0, -2), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bore, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Freeform ergonomic shaft grip sleeve')

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
