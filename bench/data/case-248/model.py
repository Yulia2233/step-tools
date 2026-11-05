from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: rectangular-to-round-transition-pedestal (build, profile=geometry) ----
    base_sketch = scad.make_sketch_rsketch(name='rectangular_foot', plane='XY')
    base_sketch = scad.add_point_rsketch(sketch=base_sketch, point_id='a', x=-40.0, y=-25.0)
    base_sketch = scad.add_point_rsketch(sketch=base_sketch, point_id='b', x=40.0, y=-25.0)
    base_sketch = scad.add_point_rsketch(sketch=base_sketch, point_id='c', x=40.0, y=25.0)
    base_sketch = scad.add_point_rsketch(sketch=base_sketch, point_id='d', x=-40.0, y=25.0)
    base_sketch = scad.add_line_rsketch(sketch=base_sketch, entity_id='ab', start='a', end='b')
    base_sketch = scad.add_line_rsketch(sketch=base_sketch, entity_id='bc', start='b', end='c')
    base_sketch = scad.add_line_rsketch(sketch=base_sketch, entity_id='cd', start='c', end='d')
    base_sketch = scad.add_line_rsketch(sketch=base_sketch, entity_id='da', start='d', end='a')
    base_wire = scad.make_wire_from_sketch_rwire(sketch=base_sketch)
    crown_sketch = scad.make_sketch_rsketch(name='round_crown', plane={'origin': (6.0, 0.0, 50.0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    crown_sketch = scad.add_point_rsketch(sketch=crown_sketch, point_id='center', x=0.0, y=0.0)
    crown_sketch = scad.add_circle_rsketch(sketch=crown_sketch, entity_id='crown', center='center', radius=18.0)
    crown_wire = scad.make_wire_from_sketch_rwire(sketch=crown_sketch)
    result = scad.loft_rsolid(profiles=[base_wire, crown_wire], ruled=True)

    # ---- feature: instrument-mounting-boss (add, profile=geometry) ----
    boss = scad.make_cylinder_rsolid(radius=12.0, height=15.0, bottom_face_center=(6.0, 0.0, 49.0), axis=(0, 0, 1))
    result = scad.union_rsolid(result, boss, clean=True)

    # ---- feature: blind-instrument-socket (subtract, profile=geometry) ----
    socket = scad.make_cylinder_rsolid(radius=5.0, height=11.0, bottom_face_center=(6.0, 0.0, 54.0), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, socket, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Ruled transition instrument pedestal')

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
