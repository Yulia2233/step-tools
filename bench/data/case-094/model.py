from pathlib import Path
import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: mounting-stock (build, profile=geometry) ----
    result = scad.make_box_rsolid(width=98.0, height=64.0, depth=10.0, bottom_face_center=(0.0, 0.0, 0.0))
    
    # ---- feature: ql-top-perimeter-bevel (modify, profile=geometry) ----
    rim = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='LINE')).where(predicate=scad.ql.prop(path='geom.center.z', op='>', value_=9.999)).exactly(count=4).resolve(scope=result))
    _rim_volume = result.get_volume()
    result = scad.chamfer_rsolid(solid=result, edges=rim, distance=0.7, generated_faces_tag='feature.mount-rim-bevel')
    assert 0 < result.get_volume() < _rim_volume - 1e-5
    
    # ---- feature: ql-bottom-perimeter-round (modify, profile=geometry) ----
    bottom_edges = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='LINE')).where(predicate=scad.ql.prop(path='geom.center.z', op='<', value_=0.001)).exactly(count=4).resolve(scope=result))
    result = scad.fillet_rsolid(solid=result, edges=bottom_edges, radius=0.5, generated_faces_tag='feature.mount-bottom-round')
    
    # ---- feature: saddle-cradle-stock (add, profile=geometry) ----
    cradle = scad.make_box_rsolid(width=72.0, height=38.0, depth=26.0, bottom_face_center=(0.0, 0.0, 9.0))
    _volume_before_1 = result.get_volume()
    result = scad.union_rsolid(result, cradle)
    assert result.get_volume() > _volume_before_1 + 1e-5, "additive feature must add volume"
    
    # ---- feature: longitudinal-open-rail-seat (subtract, profile=geometry) ----
    rail_seat = scad.make_cylinder_rsolid(radius=12.5, height=78.0, bottom_face_center=(-39.0, 0.0, 33.0), axis=(1.0, 0.0, 0.0))
    _volume_before_2 = result.get_volume()
    result = scad.cut_rsolid(result, rail_seat, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_2 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: elongated-fastening-slots (subtract, profile=geometry) ----
    slot_end_0a = scad.make_cylinder_rsolid(radius=2.6, height=12.0, bottom_face_center=(-41.0, -5.0, -1.0), axis=(0.0, 0.0, 1.0))
    slot_end_0b = scad.make_cylinder_rsolid(radius=2.6, height=12.0, bottom_face_center=(-41.0, 5.0, -1.0), axis=(0.0, 0.0, 1.0))
    slot_mid_0 = scad.make_box_rsolid(width=5.2, height=10.0, depth=12.0, bottom_face_center=(-41.0, 0.0, -1.0))
    slot_tool_0 = scad.union_rsolid(slot_end_0a, slot_mid_0, slot_end_0b)
    _volume_before_3 = result.get_volume()
    result = scad.cut_rsolid(result, slot_tool_0, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_3 - 1e-5, "subtractive feature must remove volume"
    slot_end_1a = scad.make_cylinder_rsolid(radius=2.6, height=12.0, bottom_face_center=(41.0, -5.0, -1.0), axis=(0.0, 0.0, 1.0))
    slot_end_1b = scad.make_cylinder_rsolid(radius=2.6, height=12.0, bottom_face_center=(41.0, 5.0, -1.0), axis=(0.0, 0.0, 1.0))
    slot_mid_1 = scad.make_box_rsolid(width=5.2, height=10.0, depth=12.0, bottom_face_center=(41.0, 0.0, -1.0))
    slot_tool_1 = scad.union_rsolid(slot_end_1a, slot_mid_1, slot_end_1b)
    _volume_before_4 = result.get_volume()
    result = scad.cut_rsolid(result, slot_tool_1, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_4 - 1e-5, "subtractive feature must remove volume"
    
    assert len(scad.ql.solids().exactly(count=1).resolve(scope=result)) == 1
    return scad.make_part_rpart(part_id='part', body=result, name='open-cylindrical-rail-saddle')

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
