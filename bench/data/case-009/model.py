from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: continuous-helical-rib (build, profile=geometry) ----
    rib_profile_sketch = scad.make_sketch_rsketch(name='rib_profile', plane={'origin': (8.5, 0, 0), 'x_axis': (0, 0, 1), 'y_axis': (1, 0, 0)})
    rib_profile_sketch = scad.add_point_rsketch(sketch=rib_profile_sketch, point_id='c', x=0.0, y=0.0)
    rib_profile_sketch = scad.add_circle_rsketch(sketch=rib_profile_sketch, entity_id='circle', center='c', radius=1.6)
    rib_profile = scad.make_wire_from_sketch_rwire(sketch=rib_profile_sketch)
    result = scad.helical_sweep_rsolid(profile=rib_profile, pitch=8, height=24, radius=8.5, center=(0,0,0), dir=(0,0,1), handedness='Left')
    
    # ---- feature: sleeve-core-and-end-seats (add, profile=geometry) ----
    core = scad.make_cylinder_rsolid(radius=7.4, height=26.0, bottom_face_center=(0, 0, -1), axis=(0, 0, 1))
    lower_seat = scad.make_cylinder_rsolid(radius=12.0, height=4.0, bottom_face_center=(0, 0, -2), axis=(0, 0, 1))
    upper_seat = scad.make_cylinder_rsolid(radius=12.0, height=4.0, bottom_face_center=(0, 0, 22), axis=(0, 0, 1))
    result = scad.union_rsolid(result, core, lower_seat, upper_seat)
    
    # ---- feature: central-functional-bore (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=3.2, height=32.0, bottom_face_center=(0, 0, -4), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bore, skip_non_intersecting=False)
    
    # ---- feature: end-seat-2-fasteners (subtract, profile=geometry) ----
    lo_bolt0 = scad.make_cylinder_rsolid(radius=1.0, height=6.0, bottom_face_center=(7.07107, 7.07107, -3), axis=(0, 0, 1))
    hi_bolt0 = scad.make_cylinder_rsolid(radius=1.0, height=6.0, bottom_face_center=(7.07107, 7.07107, 21), axis=(0, 0, 1))
    lo_bolt1 = scad.make_cylinder_rsolid(radius=1.0, height=6.0, bottom_face_center=(-7.07107, -7.07107, -3), axis=(0, 0, 1))
    hi_bolt1 = scad.make_cylinder_rsolid(radius=1.0, height=6.0, bottom_face_center=(-7.07107, -7.07107, 21), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, lo_bolt0, hi_bolt0, lo_bolt1, hi_bolt1, skip_non_intersecting=False)
    
    # ---- feature: radial-oil-port (subtract, profile=geometry) ----
    oil = scad.make_cylinder_rsolid(radius=1.2, height=28.0, bottom_face_center=(-14, 0, 12.0), axis=(1, 0, 0))
    result = scad.cut_rsolid(result, oil, skip_non_intersecting=False)
    
    # ---- feature: end-bore-leadin (subtract, profile=geometry) ----
    leadin = scad.make_cone_rsolid(bottom_radius=3.2, top_radius=4.1, height=1.1, bottom_face_center=(0,0,25.2), axis=(0,0,1))
    result = scad.cut_rsolid(result, leadin, skip_non_intersecting=False)
    
    return scad.make_part_rpart(part_id='part', body=result, name='Helically ribbed thermal sleeve variant 4')

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
