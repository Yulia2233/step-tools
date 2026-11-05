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
    
    # ---- feature: 3-point-mounting-bores (subtract, profile=geometry) ----
    bolt_0 = scad.make_cylinder_rsolid(radius=2.5, height=12.0, bottom_face_center=(-41.0, -24.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_3 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_0, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_3 - 1e-5, "subtractive feature must remove volume"
    bolt_1 = scad.make_cylinder_rsolid(radius=2.5, height=12.0, bottom_face_center=(41.0, 24.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_4 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_1, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_4 - 1e-5, "subtractive feature must remove volume"
    bolt_2 = scad.make_cylinder_rsolid(radius=2.5, height=12.0, bottom_face_center=(-41.0, 24.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_5 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_2, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_5 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: bolt-head-counterbores (subtract, profile=geometry) ----
    counterbore_0 = scad.make_cylinder_rsolid(radius=4.2, height=3.3, bottom_face_center=(-41.0, -24.0, 6.8), axis=(0.0, 0.0, 1.0))
    _volume_before_6 = result.get_volume()
    result = scad.cut_rsolid(result, counterbore_0, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_6 - 1e-5, "subtractive feature must remove volume"
    counterbore_1 = scad.make_cylinder_rsolid(radius=4.2, height=3.3, bottom_face_center=(41.0, 24.0, 6.8), axis=(0.0, 0.0, 1.0))
    _volume_before_7 = result.get_volume()
    result = scad.cut_rsolid(result, counterbore_1, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_7 - 1e-5, "subtractive feature must remove volume"
    counterbore_2 = scad.make_cylinder_rsolid(radius=4.2, height=3.3, bottom_face_center=(-41.0, 24.0, 6.8), axis=(0.0, 0.0, 1.0))
    _volume_before_8 = result.get_volume()
    result = scad.cut_rsolid(result, counterbore_2, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_8 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: ql-post-boolean-fastener-exit-rims (modify, profile=geometry) ----
    exit_rims = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='CIRCLE')).where(predicate=scad.ql.prop(path='geom.center.z', op='>', value_=-0.001)).where(predicate=scad.ql.prop(path='geom.center.z', op='<', value_=0.001)).where(predicate=scad.ql.or_(scad.ql.prop(path='geom.center.x', op='<', value_=-40.9), scad.ql.prop(path='geom.center.x', op='>', value_=40.9))).exactly(count=3).resolve(scope=result))
    _exit_volume = result.get_volume()
    result = scad.chamfer_rsolid(solid=result, edges=exit_rims, distance=0.25, generated_faces_tag='feature.fastener-exit-bevel')
    assert 0 < result.get_volume() < _exit_volume - 1e-5
    
    # ---- feature: underside-lightening-recess (subtract, profile=geometry) ----
    recess = scad.make_box_rsolid(width=33.32, height=22.4, depth=4.4, bottom_face_center=(0.0, 0.0, -1.0))
    _volume_before_9 = result.get_volume()
    result = scad.cut_rsolid(result, recess, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_9 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: rear-cable-anchor-pad (add, profile=geometry) ----
    anchor_pad = scad.make_box_rsolid(width=14.0, height=11.0, depth=7.0, bottom_face_center=(0.0, 28.0, 9.0))
    _volume_before_10 = result.get_volume()
    result = scad.union_rsolid(result, anchor_pad)
    assert result.get_volume() > _volume_before_10 + 1e-5, "additive feature must add volume"
    
    # ---- feature: cable-anchor-bore (subtract, profile=geometry) ----
    anchor_bore = scad.make_cylinder_rsolid(radius=1.7, height=20.0, bottom_face_center=(0.0, 28.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_11 = result.get_volume()
    result = scad.cut_rsolid(result, anchor_bore, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_11 - 1e-5, "subtractive feature must remove volume"
    
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
