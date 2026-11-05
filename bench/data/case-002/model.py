from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: intersecting-spline-network-skin (build, profile=geometry) ----
    profiles = []
    edge = scad.make_spline_redge(control_points=[[-12, -10, 0.0], [0, -10, 6.48], [12, -10, 0.0]], degree=2, knots=[0.0,1.0], multiplicities=[3,3])
    profiles.append(edge)
    edge = scad.make_spline_redge(control_points=[[-12, 0, 1.96], [0, 0, 8.44], [12, 0, 1.96]], degree=2, knots=[0.0,1.0], multiplicities=[3,3])
    profiles.append(edge)
    edge = scad.make_spline_redge(control_points=[[-12, 10, 0.0], [0, 10, 6.48], [12, 10, 0.0]], degree=2, knots=[0.0,1.0], multiplicities=[3,3])
    profiles.append(edge)
    guides = []
    edge = scad.make_spline_redge(control_points=[[-12, -10, 0.0], [-12, 0, 3.92], [-12, 10, 0.0]], degree=2, knots=[0.0,1.0], multiplicities=[3,3])
    guides.append(edge)
    edge = scad.make_spline_redge(control_points=[[0, -10, 3.24], [0, 0, 7.16], [0, 10, 3.24]], degree=2, knots=[0.0,1.0], multiplicities=[3,3])
    guides.append(edge)
    edge = scad.make_spline_redge(control_points=[[12, -10, 0.0], [12, 0, 3.92], [12, 10, 0.0]], degree=2, knots=[0.0,1.0], multiplicities=[3,3])
    guides.append(edge)
    skin = scad.make_gordon_surface_rface(profiles=profiles, guides=guides, tolerance=0.0005)
    result = scad.extrude_rsolid(profile=skin, direction=(0,0,1), distance=2.5)
    
    # ---- feature: integral-gasket-land (add, profile=geometry) ----
    land = scad.make_box_rsolid(width=36.0, height=30.0, depth=4.0, bottom_face_center=(0, 0, -2))
    result = scad.union_rsolid(result, land)
    
    # ---- feature: underside-access-pocket (subtract, profile=geometry) ----
    pocket = scad.make_box_rsolid(width=20.0, height=13.0, depth=6.0, bottom_face_center=(0, 0, -3))
    result = scad.cut_rsolid(result, pocket, skip_non_intersecting=False)
    
    # ---- feature: mounting-pattern-4-holes (subtract, profile=geometry) ----
    bolt_0 = scad.make_cylinder_rsolid(radius=1.5, height=7.0, bottom_face_center=(-14.0, -10.0, -3), axis=(0, 0, 1))
    bolt_1 = scad.make_cylinder_rsolid(radius=1.5, height=7.0, bottom_face_center=(14.0, -10.0, -3), axis=(0, 0, 1))
    bolt_2 = scad.make_cylinder_rsolid(radius=1.5, height=7.0, bottom_face_center=(14.0, 10.0, -3), axis=(0, 0, 1))
    bolt_3 = scad.make_cylinder_rsolid(radius=1.5, height=7.0, bottom_face_center=(-14.0, 10.0, -3), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bolt_0, bolt_1, bolt_2, bolt_3, skip_non_intersecting=False)
    
    # ---- feature: counterbored-fastener-seats (subtract, profile=geometry) ----
    bolt_seat_0 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(-14.0, -10.0, 0.5), axis=(0, 0, 1))
    bolt_seat_1 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(14.0, -10.0, 0.5), axis=(0, 0, 1))
    bolt_seat_2 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(14.0, 10.0, 0.5), axis=(0, 0, 1))
    bolt_seat_3 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(-14.0, 10.0, 0.5), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bolt_seat_0, bolt_seat_1, bolt_seat_2, bolt_seat_3, skip_non_intersecting=False)
    
    return scad.make_part_rpart(part_id='part', body=result, name='Gordon-surface instrument cover variant 2')

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
