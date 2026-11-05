from pathlib import Path
import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: mounting-stock (build, profile=geometry) ----
    result = scad.make_box_rsolid(width=106.0, height=70.0, depth=9.0, bottom_face_center=(0.0, 0.0, 0.0))
    
    # ---- feature: ql-top-perimeter-round (modify, profile=geometry) ----
    rim = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='LINE')).where(predicate=scad.ql.prop(path='geom.center.z', op='>', value_=8.999)).exactly(count=4).resolve(scope=result))
    _rim_volume = result.get_volume()
    result = scad.fillet_rsolid(solid=result, edges=rim, radius=0.8, generated_faces_tag='feature.mount-rim-round')
    assert 0 < result.get_volume() < _rim_volume - 1e-5
    
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
    
    # ---- feature: 4-point-mounting-bores (subtract, profile=geometry) ----
    bolt_0 = scad.make_cylinder_rsolid(radius=2.5, height=11.0, bottom_face_center=(-45.0, -27.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_5 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_0, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_5 - 1e-5, "subtractive feature must remove volume"
    bolt_1 = scad.make_cylinder_rsolid(radius=2.5, height=11.0, bottom_face_center=(45.0, 27.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_6 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_1, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_6 - 1e-5, "subtractive feature must remove volume"
    bolt_2 = scad.make_cylinder_rsolid(radius=2.5, height=11.0, bottom_face_center=(-45.0, 27.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_7 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_2, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_7 - 1e-5, "subtractive feature must remove volume"
    bolt_3 = scad.make_cylinder_rsolid(radius=2.5, height=11.0, bottom_face_center=(45.0, -27.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_8 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_3, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_8 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: bolt-head-counterbores (subtract, profile=geometry) ----
    counterbore_0 = scad.make_cylinder_rsolid(radius=4.2, height=3.3, bottom_face_center=(-45.0, -27.0, 5.8), axis=(0.0, 0.0, 1.0))
    _volume_before_9 = result.get_volume()
    result = scad.cut_rsolid(result, counterbore_0, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_9 - 1e-5, "subtractive feature must remove volume"
    counterbore_1 = scad.make_cylinder_rsolid(radius=4.2, height=3.3, bottom_face_center=(45.0, 27.0, 5.8), axis=(0.0, 0.0, 1.0))
    _volume_before_10 = result.get_volume()
    result = scad.cut_rsolid(result, counterbore_1, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_10 - 1e-5, "subtractive feature must remove volume"
    counterbore_2 = scad.make_cylinder_rsolid(radius=4.2, height=3.3, bottom_face_center=(-45.0, 27.0, 5.8), axis=(0.0, 0.0, 1.0))
    _volume_before_11 = result.get_volume()
    result = scad.cut_rsolid(result, counterbore_2, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_11 - 1e-5, "subtractive feature must remove volume"
    counterbore_3 = scad.make_cylinder_rsolid(radius=4.2, height=3.3, bottom_face_center=(45.0, -27.0, 5.8), axis=(0.0, 0.0, 1.0))
    _volume_before_12 = result.get_volume()
    result = scad.cut_rsolid(result, counterbore_3, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_12 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: ql-post-boolean-fastener-exit-rims (modify, profile=geometry) ----
    exit_rims = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='CIRCLE')).where(predicate=scad.ql.prop(path='geom.center.z', op='>', value_=-0.001)).where(predicate=scad.ql.prop(path='geom.center.z', op='<', value_=0.001)).where(predicate=scad.ql.or_(scad.ql.prop(path='geom.center.x', op='<', value_=-44.9), scad.ql.prop(path='geom.center.x', op='>', value_=44.9))).exactly(count=4).resolve(scope=result))
    _exit_volume = result.get_volume()
    result = scad.fillet_rsolid(solid=result, edges=exit_rims, radius=0.3, generated_faces_tag='feature.fastener-exit-round')
    assert 0 < result.get_volume() < _exit_volume - 1e-5
    
    # ---- feature: underside-lightening-recess (subtract, profile=geometry) ----
    recess = scad.make_box_rsolid(width=36.04, height=24.5, depth=4.4, bottom_face_center=(0.0, 0.0, -1.0))
    _volume_before_13 = result.get_volume()
    result = scad.cut_rsolid(result, recess, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_13 - 1e-5, "subtractive feature must remove volume"
    
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
