from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: circular-grip-section (build, profile=geometry) ----
    section_sketch = scad.make_sketch_rsketch(name='grip_section', plane='XY')
    section_sketch = scad.add_point_rsketch(sketch=section_sketch, point_id='c', x=0.0, y=0.0)
    section_sketch = scad.add_circle_rsketch(sketch=section_sketch, entity_id='circle', center='c', radius=7.0)
    section_wire = scad.make_wire_from_sketch_rwire(sketch=section_sketch)
    section = scad.make_face_from_wire_rface(wire=section_wire)

    # ---- feature: planar-s-shaped-grip (build, profile=geometry) ----
    rail_edge = scad.make_spline_redge(control_points=[[0.0, 0.0, 0.0], [0.0, 0.0, 28.0], [16.0, 0.0, 48.0], [32.0, 0.0, 68.0], [32.0, 0.0, 96.0]], degree=3, knots=[0.0, 0.5, 1.0], multiplicities=[4, 1, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    result = scad.sweep_rsolid(profile=section, path=rail, is_frenet=True)

    # ---- feature: eased-grip-end-rims (modify, profile=geometry) ----
    end_rims = scad.ql.edges().where(predicate=scad.ql.prop(path='geom.length', op='<', value_=45.0)).exactly(count=2)
    result = scad.chamfer_rsolid(solid=result, edges=end_rims, distance=0.8)

    return scad.make_part_rpart(part_id='part', body=result, name='S-offset equipment grip')

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
