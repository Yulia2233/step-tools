from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: s-curved-grip (build, profile=geometry) ----
    profile_sketch = scad.make_sketch_rsketch(name='grip_section', plane={'origin': (0.0, 0.0, 0.0), 'x_axis': (0.4061384661, -0.9138115486, 0.0), 'y_axis': (0.0, 0.0, -1.0)})
    profile_sketch = scad.add_point_rsketch(sketch=profile_sketch, point_id='c', x=0.0, y=0.0)
    profile_sketch = scad.add_circle_rsketch(sketch=profile_sketch, entity_id='circle', center='c', radius=8.0)
    profile = scad.make_face_from_sketch_rface(sketch=profile_sketch)
    rail_edge = scad.make_spline_redge(control_points=[[0.0, 0.0, 0.0], [18.0, 8.0, 0.0], [36.0, 0.0, 0.0], [54.0, -8.0, 0.0], [72.0, 0.0, 0.0]], degree=3, knots=[0.0, 0.5, 1.0], multiplicities=[4, 1, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=True)

    # ---- feature: transverse-retaining-pin-hole (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=2.5, height=24.0, bottom_face_center=(12.0, 4.0, -12.0), axis=(0.0, 0.0, 1.0))
    result = scad.cut_rsolid(result, bore, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='S-curved retaining-pin handle')

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
