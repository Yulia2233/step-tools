from pathlib import Path
import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: mounting-stock (build, profile=geometry) ----
    result = scad.make_box_rsolid(width=78.0, height=58.0, depth=9.0, bottom_face_center=(0.0, 0.0, 0.0))
    
    # ---- feature: ql-top-perimeter-round (modify, profile=geometry) ----
    rim = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='LINE')).where(predicate=scad.ql.prop(path='geom.center.z', op='>', value_=8.999)).exactly(count=4).resolve(scope=result))
    _rim_volume = result.get_volume()
    result = scad.fillet_rsolid(solid=result, edges=rim, radius=0.8, generated_faces_tag='feature.mount-rim-round')
    assert 0 < result.get_volume() < _rim_volume - 1e-5
    
    # ---- feature: ql-bottom-perimeter-bevel (modify, profile=geometry) ----
    bottom_edges = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='LINE')).where(predicate=scad.ql.prop(path='geom.center.z', op='<', value_=0.001)).exactly(count=4).resolve(scope=result))
    result = scad.chamfer_rsolid(solid=result, edges=bottom_edges, distance=0.45, generated_faces_tag='feature.mount-bottom-bevel')
    
    # ---- feature: separated-pin-support-ears (add, profile=geometry) ----
    ear_0 = scad.make_box_rsolid(width=10.0, height=28.0, depth=32.0, bottom_face_center=(-18.0, 0.0, 8.0))
    _volume_before_1 = result.get_volume()
    result = scad.union_rsolid(result, ear_0)
    assert result.get_volume() > _volume_before_1 + 1e-5, "additive feature must add volume"
    ear_1 = scad.make_box_rsolid(width=10.0, height=28.0, depth=32.0, bottom_face_center=(18.0, 0.0, 8.0))
    _volume_before_2 = result.get_volume()
    result = scad.union_rsolid(result, ear_1)
    assert result.get_volume() > _volume_before_2 + 1e-5, "additive feature must add volume"
    
    # ---- feature: coaxial-clevis-pin-bore (subtract, profile=geometry) ----
    pin_bore = scad.make_cylinder_rsolid(radius=5.5, height=52.0, bottom_face_center=(-26.0, 0.0, 29.0), axis=(1.0, 0.0, 0.0))
    _volume_before_3 = result.get_volume()
    result = scad.cut_rsolid(result, pin_bore, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_3 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: 4-point-mounting-bores (subtract, profile=geometry) ----
    bolt_0 = scad.make_cylinder_rsolid(radius=2.5, height=11.0, bottom_face_center=(-31.0, -21.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_4 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_0, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_4 - 1e-5, "subtractive feature must remove volume"
    bolt_1 = scad.make_cylinder_rsolid(radius=2.5, height=11.0, bottom_face_center=(31.0, 21.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_5 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_1, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_5 - 1e-5, "subtractive feature must remove volume"
    bolt_2 = scad.make_cylinder_rsolid(radius=2.5, height=11.0, bottom_face_center=(-31.0, 21.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_6 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_2, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_6 - 1e-5, "subtractive feature must remove volume"
    bolt_3 = scad.make_cylinder_rsolid(radius=2.5, height=11.0, bottom_face_center=(31.0, -21.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_7 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_3, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_7 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: bolt-entry-countersinks (subtract, profile=geometry) ----
    countersink_0 = scad.make_cone_rsolid(bottom_radius=2.45, top_radius=4.55, height=2.1, bottom_face_center=(-31.0, -21.0, 7.0), axis=(0.0, 0.0, 1.0))
    _volume_before_8 = result.get_volume()
    result = scad.cut_rsolid(result, countersink_0, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_8 - 1e-5, "subtractive feature must remove volume"
    countersink_1 = scad.make_cone_rsolid(bottom_radius=2.45, top_radius=4.55, height=2.1, bottom_face_center=(31.0, 21.0, 7.0), axis=(0.0, 0.0, 1.0))
    _volume_before_9 = result.get_volume()
    result = scad.cut_rsolid(result, countersink_1, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_9 - 1e-5, "subtractive feature must remove volume"
    countersink_2 = scad.make_cone_rsolid(bottom_radius=2.45, top_radius=4.55, height=2.1, bottom_face_center=(-31.0, 21.0, 7.0), axis=(0.0, 0.0, 1.0))
    _volume_before_10 = result.get_volume()
    result = scad.cut_rsolid(result, countersink_2, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_10 - 1e-5, "subtractive feature must remove volume"
    countersink_3 = scad.make_cone_rsolid(bottom_radius=2.45, top_radius=4.55, height=2.1, bottom_face_center=(31.0, -21.0, 7.0), axis=(0.0, 0.0, 1.0))
    _volume_before_11 = result.get_volume()
    result = scad.cut_rsolid(result, countersink_3, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_11 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: ql-post-boolean-fastener-exit-rims (modify, profile=geometry) ----
    exit_rims = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='CIRCLE')).where(predicate=scad.ql.prop(path='geom.center.z', op='>', value_=-0.001)).where(predicate=scad.ql.prop(path='geom.center.z', op='<', value_=0.001)).where(predicate=scad.ql.or_(scad.ql.prop(path='geom.center.x', op='<', value_=-30.9), scad.ql.prop(path='geom.center.x', op='>', value_=30.9))).exactly(count=4).resolve(scope=result))
    _exit_volume = result.get_volume()
    result = scad.fillet_rsolid(solid=result, edges=exit_rims, radius=0.3, generated_faces_tag='feature.fastener-exit-round')
    assert 0 < result.get_volume() < _exit_volume - 1e-5
    
    # ---- feature: front-anti-rotation-keyway (subtract, profile=geometry) ----
    keyway = scad.make_box_rsolid(width=6.0, height=6.0, depth=11.0, bottom_face_center=(0.0, -27.5, -1.0))
    _volume_before_12 = result.get_volume()
    result = scad.cut_rsolid(result, keyway, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_12 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: rear-cable-anchor-pad (add, profile=geometry) ----
    anchor_pad = scad.make_box_rsolid(width=14.0, height=11.0, depth=7.0, bottom_face_center=(0.0, 25.0, 8.0))
    _volume_before_13 = result.get_volume()
    result = scad.union_rsolid(result, anchor_pad)
    assert result.get_volume() > _volume_before_13 + 1e-5, "additive feature must add volume"
    
    # ---- feature: cable-anchor-bore (subtract, profile=geometry) ----
    anchor_bore = scad.make_cylinder_rsolid(radius=1.7, height=19.0, bottom_face_center=(0.0, 25.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_14 = result.get_volume()
    result = scad.cut_rsolid(result, anchor_bore, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_14 - 1e-5, "subtractive feature must remove volume"
    
    assert len(scad.ql.solids().exactly(count=1).resolve(scope=result)) == 1
    return scad.make_part_rpart(part_id='part', body=result, name='twin-ear-actuator-clevis')

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
