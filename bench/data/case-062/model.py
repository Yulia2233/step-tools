from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: continuous-twisted-strap (build, profile=geometry) ----
    strap_section_sketch = scad.make_sketch_rsketch(name='strap_section', plane={'origin': (0, 0, 0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    strap_section_sketch = scad.add_point_rsketch(sketch=strap_section_sketch, point_id='p0', x=-11.0, y=-3.0)
    strap_section_sketch = scad.add_point_rsketch(sketch=strap_section_sketch, point_id='p1', x=11.0, y=-3.0)
    strap_section_sketch = scad.add_point_rsketch(sketch=strap_section_sketch, point_id='p2', x=11.0, y=3.0)
    strap_section_sketch = scad.add_point_rsketch(sketch=strap_section_sketch, point_id='p3', x=-11.0, y=3.0)
    strap_section_sketch = scad.add_line_rsketch(sketch=strap_section_sketch, entity_id='e0', start='p0', end='p1')
    strap_section_sketch = scad.add_line_rsketch(sketch=strap_section_sketch, entity_id='e1', start='p1', end='p2')
    strap_section_sketch = scad.add_line_rsketch(sketch=strap_section_sketch, entity_id='e2', start='p2', end='p3')
    strap_section_sketch = scad.add_line_rsketch(sketch=strap_section_sketch, entity_id='e3', start='p3', end='p0')
    strap_section = scad.make_face_from_sketch_rface(sketch=strap_section_sketch)
    result = scad.twisted_sweep_rsolid(profile=strap_section, distance=37, twist_angle=24, axis=(0,0,1), origin=(0,0,0))
    
    # ---- feature: integral-lower-mounting-flange (add, profile=geometry) ----
    flange = scad.make_box_rsolid(width=40.0, height=28.0, depth=5.0, bottom_face_center=(0, 0, -2))
    result = scad.union_rsolid(result, flange)
    
    # ---- feature: upper-circular-register (add, profile=geometry) ----
    register = scad.make_cylinder_rsolid(radius=9.0, height=5.0, bottom_face_center=(0, 0, 35), axis=(0, 0, 1))
    result = scad.union_rsolid(result, register)
    
    # ---- feature: axial-cable-passage (subtract, profile=geometry) ----
    cable = scad.make_cylinder_rsolid(radius=1.8, height=46.0, bottom_face_center=(0, 0, -3), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, cable, skip_non_intersecting=False)
    
    # ---- feature: mounting-pattern-4-holes (subtract, profile=geometry) ----
    bolt_0 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(-15.0, -8.0, -3), axis=(0, 0, 1))
    bolt_1 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(15.0, -8.0, -3), axis=(0, 0, 1))
    bolt_2 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(15.0, 8.0, -3), axis=(0, 0, 1))
    bolt_3 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(-15.0, 8.0, -3), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bolt_0, bolt_1, bolt_2, bolt_3, skip_non_intersecting=False)
    
    # ---- feature: counterbored-fastener-seats (subtract, profile=geometry) ----
    bolt_seat_0 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(-15.0, -8.0, 1.5), axis=(0, 0, 1))
    bolt_seat_1 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(15.0, -8.0, 1.5), axis=(0, 0, 1))
    bolt_seat_2 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(15.0, 8.0, 1.5), axis=(0, 0, 1))
    bolt_seat_3 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(-15.0, 8.0, 1.5), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bolt_seat_0, bolt_seat_1, bolt_seat_2, bolt_seat_3, skip_non_intersecting=False)
    
    return scad.make_part_rpart(part_id='part', body=result, name='Twisted mounting strap variant 2')

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
