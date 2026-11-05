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
    
    # ---- feature: 2-point-mounting-bores (subtract, profile=geometry) ----
    bolt_0 = scad.make_cylinder_rsolid(radius=2.5, height=11.0, bottom_face_center=(-31.0, -21.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_4 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_0, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_4 - 1e-5, "subtractive feature must remove volume"
    bolt_1 = scad.make_cylinder_rsolid(radius=2.5, height=11.0, bottom_face_center=(31.0, 21.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_5 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_1, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_5 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: ql-post-boolean-fastener-exit-rims (modify, profile=geometry) ----
    exit_rims = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='CIRCLE')).where(predicate=scad.ql.prop(path='geom.center.z', op='>', value_=-0.001)).where(predicate=scad.ql.prop(path='geom.center.z', op='<', value_=0.001)).where(predicate=scad.ql.or_(scad.ql.prop(path='geom.center.x', op='<', value_=-30.9), scad.ql.prop(path='geom.center.x', op='>', value_=30.9))).exactly(count=2).resolve(scope=result))
    _exit_volume = result.get_volume()
    result = scad.fillet_rsolid(solid=result, edges=exit_rims, radius=0.3, generated_faces_tag='feature.fastener-exit-round')
    assert 0 < result.get_volume() < _exit_volume - 1e-5
    
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
