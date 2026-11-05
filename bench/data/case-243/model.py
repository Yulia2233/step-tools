from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: oval-to-round-grip-blank (build, profile=geometry) ----
    oval_edge = scad.make_spline_redge(
        control_points=[[19.0, 0.0, 0.0], [19.0, 7.18, 0.0],
                        [10.49, 13.0, 0.0], [0.0, 13.0, 0.0],
                        [-10.49, 13.0, 0.0], [-19.0, 7.18, 0.0],
                        [-19.0, 0.0, 0.0], [-19.0, -7.18, 0.0],
                        [-10.49, -13.0, 0.0], [0.0, -13.0, 0.0],
                        [10.49, -13.0, 0.0], [19.0, -7.18, 0.0],
                        [19.0, 0.0, 0.0]],
        degree=3, knots=[0.0, 1.0, 2.0, 3.0, 4.0],
        multiplicities=[4, 3, 3, 3, 4])
    palm_section = scad.make_wire_from_edges_rwire(edges=[oval_edge])
    neck_sketch = scad.make_sketch_rsketch(name='round_neck', plane={
        'origin': (4.0, 0.0, 45.0),
        'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    neck_sketch = scad.add_point_rsketch(sketch=neck_sketch, point_id='c', x=0.0, y=0.0)
    neck_sketch = scad.add_circle_rsketch(sketch=neck_sketch, entity_id='neck', center='c', radius=9.0)
    neck_section = scad.make_wire_from_sketch_rwire(sketch=neck_sketch)
    result = scad.loft_rsolid(profiles=[palm_section, neck_section], ruled=True)

    return scad.make_part_rpart(part_id='part', body=result, name='Ruled oval-to-round ergonomic grip blank')

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
