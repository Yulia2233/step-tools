from pathlib import Path
import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: mounting-stock (build, profile=geometry) ----
    result = scad.make_box_rsolid(width=106.0, height=70.0, depth=9.0, bottom_face_center=(0.0, 0.0, 0.0))
    
    # ---- feature: ql-top-perimeter-bevel (modify, profile=geometry) ----
    rim = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='LINE')).where(predicate=scad.ql.prop(path='geom.center.z', op='>', value_=8.999)).exactly(count=4).resolve(scope=result))
    _rim_volume = result.get_volume()
    result = scad.chamfer_rsolid(solid=result, edges=rim, distance=0.7, generated_faces_tag='feature.mount-rim-bevel')
    assert 0 < result.get_volume() < _rim_volume - 1e-5
    
    # ---- feature: ql-bottom-perimeter-round (modify, profile=geometry) ----
    bottom_edges = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='LINE')).where(predicate=scad.ql.prop(path='geom.center.z', op='<', value_=0.001)).exactly(count=4).resolve(scope=result))
    result = scad.fillet_rsolid(solid=result, edges=bottom_edges, radius=0.5, generated_faces_tag='feature.mount-bottom-round')
    
    # ---- feature: bridge-support-pillars (add, profile=geometry) ----
    pillar_0 = scad.make_box_rsolid(width=14.0, height=30.0, depth=33.0, bottom_face_center=(-30.0, 0.0, 8.0))
    _volume_before_1 = result.get_volume()
    result = scad.union_rsolid(result, pillar_0)
    assert result.get_volume() > _volume_before_1 + 1e-5, "additive feature must add volume"
    pillar_1 = scad.make_box_rsolid(width=14.0, height=30.0, depth=33.0, bottom_face_center=(30.0, 0.0, 8.0))
    _volume_before_2 = result.get_volume()
    result = scad.union_rsolid(result, pillar_1)
    assert result.get_volume() > _volume_before_2 + 1e-5, "additive feature must add volume"
    
    # ---- feature: overhead-sensor-beam (add, profile=geometry) ----
    beam = scad.make_box_rsolid(width=74.0, height=30.0, depth=12.0, bottom_face_center=(0.0, 0.0, 33.0))
    _volume_before_3 = result.get_volume()
    result = scad.union_rsolid(result, beam)
    assert result.get_volume() > _volume_before_3 + 1e-5, "additive feature must add volume"
    
    # ---- feature: horizontal-sensor-interface (subtract, profile=geometry) ----
    sensor_bore = scad.make_cylinder_rsolid(radius=5.8, height=34.0, bottom_face_center=(0.0, -17.0, 39.0), axis=(0.0, 1.0, 0.0))
    _volume_before_4 = result.get_volume()
    result = scad.cut_rsolid(result, sensor_bore, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_4 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: vertical-sensor-lock-bore (subtract, profile=geometry) ----
    sensor_lock = scad.make_cylinder_rsolid(radius=1.8, height=12.0, bottom_face_center=(0.0, 0.0, 38.0), axis=(0.0, 0.0, 1.0))
    _volume_before_5 = result.get_volume()
    result = scad.cut_rsolid(result, sensor_lock, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_5 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: elongated-fastening-slots (subtract, profile=geometry) ----
    slot_end_0a = scad.make_cylinder_rsolid(radius=2.6, height=11.0, bottom_face_center=(-45.0, -5.0, -1.0), axis=(0.0, 0.0, 1.0))
    slot_end_0b = scad.make_cylinder_rsolid(radius=2.6, height=11.0, bottom_face_center=(-45.0, 5.0, -1.0), axis=(0.0, 0.0, 1.0))
    slot_mid_0 = scad.make_box_rsolid(width=5.2, height=10.0, depth=11.0, bottom_face_center=(-45.0, 0.0, -1.0))
    slot_tool_0 = scad.union_rsolid(slot_end_0a, slot_mid_0, slot_end_0b)
    _volume_before_6 = result.get_volume()
    result = scad.cut_rsolid(result, slot_tool_0, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_6 - 1e-5, "subtractive feature must remove volume"
    slot_end_1a = scad.make_cylinder_rsolid(radius=2.6, height=11.0, bottom_face_center=(45.0, -5.0, -1.0), axis=(0.0, 0.0, 1.0))
    slot_end_1b = scad.make_cylinder_rsolid(radius=2.6, height=11.0, bottom_face_center=(45.0, 5.0, -1.0), axis=(0.0, 0.0, 1.0))
    slot_mid_1 = scad.make_box_rsolid(width=5.2, height=10.0, depth=11.0, bottom_face_center=(45.0, 0.0, -1.0))
    slot_tool_1 = scad.union_rsolid(slot_end_1a, slot_mid_1, slot_end_1b)
    _volume_before_7 = result.get_volume()
    result = scad.cut_rsolid(result, slot_tool_1, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_7 - 1e-5, "subtractive feature must remove volume"
    
    assert len(scad.ql.solids().exactly(count=1).resolve(scope=result)) == 1
    return scad.make_part_rpart(part_id='part', body=result, name='raised-sensor-bridge-mount')

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
