from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: eccentric-ruled-grip (build, profile=geometry) ----
    base_sketch = scad.make_sketch_rsketch(name='palm_base', plane={'origin': (0, 0, 0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    base_sketch = scad.add_point_rsketch(sketch=base_sketch, point_id='c', x=0.0, y=0.0)
    base_sketch = scad.add_circle_rsketch(sketch=base_sketch, entity_id='circle', center='c', radius=18.0)
    base = scad.make_wire_from_sketch_rwire(sketch=base_sketch)
    waist_sketch = scad.make_sketch_rsketch(name='grip_waist', plane={'origin': (3, 0, 18), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    waist_sketch = scad.add_point_rsketch(sketch=waist_sketch, point_id='c', x=0.0, y=0.0)
    waist_sketch = scad.add_circle_rsketch(sketch=waist_sketch, entity_id='circle', center='c', radius=13.0)
    waist = scad.make_wire_from_sketch_rwire(sketch=waist_sketch)
    neck_sketch = scad.make_sketch_rsketch(name='boss_shoulder', plane={'origin': (5, 0, 33), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    neck_sketch = scad.add_point_rsketch(sketch=neck_sketch, point_id='c', x=0.0, y=0.0)
    neck_sketch = scad.add_circle_rsketch(sketch=neck_sketch, entity_id='circle', center='c', radius=10.0)
    neck = scad.make_wire_from_sketch_rwire(sketch=neck_sketch)
    result = scad.loft_rsolid(profiles=[base, waist, neck], ruled=True)

    # ---- feature: spindle-mounting-boss (add, profile=geometry) ----
    boss = scad.make_cylinder_rsolid(radius=8.0, height=14.0, bottom_face_center=(5, 0, 31), axis=(0, 0, 1))
    result = scad.union_rsolid(result, boss)

    # ---- feature: blind-spindle-socket (subtract, profile=geometry) ----
    socket = scad.make_cylinder_rsolid(radius=3.5, height=10.0, bottom_face_center=(5, 0, 36), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, socket, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Eccentric ruled spindle grip')

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
