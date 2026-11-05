from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: planar-s-shaped-support-stem (build, profile=geometry) ----
    profile_sketch = scad.make_sketch_rsketch(name='stem_section', plane='XY')
    profile_sketch = scad.add_point_rsketch(sketch=profile_sketch, point_id='c', x=0.0, y=0.0)
    profile_sketch = scad.add_circle_rsketch(sketch=profile_sketch, entity_id='circle', center='c', radius=2.3)
    profile = scad.make_face_from_sketch_rface(sketch=profile_sketch)
    rail_edge = scad.make_spline_redge(control_points=[[0.0, 0.0, 0.0], [0.0, 0.0, 7.0], [9.0, 0.0, 13.0], [-6.0, 0.0, 21.0], [-6.0, 0.0, 28.0]], degree=3, knots=[0.0, 0.5, 1.0], multiplicities=[4, 1, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=True)

    # ---- feature: rectangular-mounting-flange (add, profile=geometry) ----
    flange = scad.make_box_rsolid(width=18.0, height=10.0, depth=3.0, bottom_face_center=(0.0, 0.0, -1.0))
    result = scad.union_rsolid(result, flange)

    # ---- feature: two-through-bolt-holes (subtract, profile=geometry) ----
    bolt_left = scad.make_cylinder_rsolid(radius=1.5, height=5.0, bottom_face_center=(-6.0, 0.0, -2.0), axis=(0.0, 0.0, 1.0))
    bolt_right = scad.make_cylinder_rsolid(radius=1.5, height=5.0, bottom_face_center=(6.0, 0.0, -2.0), axis=(0.0, 0.0, 1.0))
    result = scad.cut_rsolid(result, bolt_left, bolt_right, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='S-curved instrument support stem')

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
