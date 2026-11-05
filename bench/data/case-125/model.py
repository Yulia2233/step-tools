from pathlib import Path
import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: mounting-stock (build, profile=geometry) ----
    result = scad.make_box_rsolid(width=88.0, height=66.0, depth=10.0, bottom_face_center=(0.0, 0.0, 0.0))
    
    # ---- feature: ql-top-perimeter-round (modify, profile=geometry) ----
    rim = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='LINE')).where(predicate=scad.ql.prop(path='geom.center.z', op='>', value_=9.999)).exactly(count=4).resolve(scope=result))
    _rim_volume = result.get_volume()
    result = scad.fillet_rsolid(solid=result, edges=rim, radius=0.8, generated_faces_tag='feature.mount-rim-round')
    assert 0 < result.get_volume() < _rim_volume - 1e-5
    
    # ---- feature: ql-bottom-perimeter-bevel (modify, profile=geometry) ----
    bottom_edges = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='LINE')).where(predicate=scad.ql.prop(path='geom.center.z', op='<', value_=0.001)).exactly(count=4).resolve(scope=result))
    result = scad.chamfer_rsolid(solid=result, edges=bottom_edges, distance=0.45, generated_faces_tag='feature.mount-bottom-bevel')
    
    # ---- feature: main-horizontal-valve-barrel (add, profile=geometry) ----
    barrel = scad.make_cylinder_rsolid(radius=13.0, height=62.0, bottom_face_center=(-31.0, 0.0, 18.0), axis=(1.0, 0.0, 0.0))
    _volume_before_1 = result.get_volume()
    result = scad.union_rsolid(result, barrel)
    assert result.get_volume() > _volume_before_1 + 1e-5, "additive feature must add volume"
    
    # ---- feature: upright-valve-neck (add, profile=geometry) ----
    neck = scad.make_cylinder_rsolid(radius=10.0, height=23.0, bottom_face_center=(0.0, 0.0, 25.0), axis=(0.0, 0.0, 1.0))
    _volume_before_2 = result.get_volume()
    result = scad.union_rsolid(result, neck)
    assert result.get_volume() > _volume_before_2 + 1e-5, "additive feature must add volume"
    
    # ---- feature: transverse-auxiliary-boss (add, profile=geometry) ----
    side_boss = scad.make_cylinder_rsolid(radius=7.0, height=27.0, bottom_face_center=(13.0, 0.0, 19.0), axis=(0.0, 1.0, 0.0))
    _volume_before_3 = result.get_volume()
    result = scad.union_rsolid(result, side_boss)
    assert result.get_volume() > _volume_before_3 + 1e-5, "additive feature must add volume"
    
    # ---- feature: main-valve-through-passage (subtract, profile=geometry) ----
    main_bore = scad.make_cylinder_rsolid(radius=6.0, height=66.0, bottom_face_center=(-33.0, 0.0, 18.0), axis=(1.0, 0.0, 0.0))
    _volume_before_4 = result.get_volume()
    result = scad.cut_rsolid(result, main_bore, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_4 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: upright-valve-passage (subtract, profile=geometry) ----
    upright_bore = scad.make_cylinder_rsolid(radius=4.3, height=32.0, bottom_face_center=(0.0, 0.0, 17.0), axis=(0.0, 0.0, 1.0))
    _volume_before_5 = result.get_volume()
    result = scad.cut_rsolid(result, upright_bore, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_5 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: auxiliary-valve-passage (subtract, profile=geometry) ----
    aux_bore = scad.make_cylinder_rsolid(radius=3.1, height=30.0, bottom_face_center=(13.0, -1.0, 19.0), axis=(0.0, 1.0, 0.0))
    _volume_before_6 = result.get_volume()
    result = scad.cut_rsolid(result, aux_bore, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_6 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: upright-port-entry-seat (subtract, profile=geometry) ----
    neck_seat = scad.make_cone_rsolid(bottom_radius=4.2, top_radius=6.8, height=2.6, bottom_face_center=(0.0, 0.0, 45.5), axis=(0.0, 0.0, 1.0))
    _volume_before_7 = result.get_volume()
    result = scad.cut_rsolid(result, neck_seat, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_7 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: 4-point-mounting-bores (subtract, profile=geometry) ----
    bolt_0 = scad.make_cylinder_rsolid(radius=2.5, height=12.0, bottom_face_center=(-36.0, -25.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_8 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_0, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_8 - 1e-5, "subtractive feature must remove volume"
    bolt_1 = scad.make_cylinder_rsolid(radius=2.5, height=12.0, bottom_face_center=(36.0, 25.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_9 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_1, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_9 - 1e-5, "subtractive feature must remove volume"
    bolt_2 = scad.make_cylinder_rsolid(radius=2.5, height=12.0, bottom_face_center=(-36.0, 25.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_10 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_2, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_10 - 1e-5, "subtractive feature must remove volume"
    bolt_3 = scad.make_cylinder_rsolid(radius=2.5, height=12.0, bottom_face_center=(36.0, -25.0, -1.0), axis=(0.0, 0.0, 1.0))
    _volume_before_11 = result.get_volume()
    result = scad.cut_rsolid(result, bolt_3, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_11 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: bolt-entry-countersinks (subtract, profile=geometry) ----
    countersink_0 = scad.make_cone_rsolid(bottom_radius=2.45, top_radius=4.55, height=2.1, bottom_face_center=(-36.0, -25.0, 8.0), axis=(0.0, 0.0, 1.0))
    _volume_before_12 = result.get_volume()
    result = scad.cut_rsolid(result, countersink_0, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_12 - 1e-5, "subtractive feature must remove volume"
    countersink_1 = scad.make_cone_rsolid(bottom_radius=2.45, top_radius=4.55, height=2.1, bottom_face_center=(36.0, 25.0, 8.0), axis=(0.0, 0.0, 1.0))
    _volume_before_13 = result.get_volume()
    result = scad.cut_rsolid(result, countersink_1, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_13 - 1e-5, "subtractive feature must remove volume"
    countersink_2 = scad.make_cone_rsolid(bottom_radius=2.45, top_radius=4.55, height=2.1, bottom_face_center=(-36.0, 25.0, 8.0), axis=(0.0, 0.0, 1.0))
    _volume_before_14 = result.get_volume()
    result = scad.cut_rsolid(result, countersink_2, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_14 - 1e-5, "subtractive feature must remove volume"
    countersink_3 = scad.make_cone_rsolid(bottom_radius=2.45, top_radius=4.55, height=2.1, bottom_face_center=(36.0, -25.0, 8.0), axis=(0.0, 0.0, 1.0))
    _volume_before_15 = result.get_volume()
    result = scad.cut_rsolid(result, countersink_3, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_15 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: ql-post-boolean-fastener-exit-rims (modify, profile=geometry) ----
    exit_rims = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='CIRCLE')).where(predicate=scad.ql.prop(path='geom.center.z', op='>', value_=-0.001)).where(predicate=scad.ql.prop(path='geom.center.z', op='<', value_=0.001)).where(predicate=scad.ql.or_(scad.ql.prop(path='geom.center.x', op='<', value_=-35.9), scad.ql.prop(path='geom.center.x', op='>', value_=35.9))).exactly(count=4).resolve(scope=result))
    _exit_volume = result.get_volume()
    result = scad.fillet_rsolid(solid=result, edges=exit_rims, radius=0.3, generated_faces_tag='feature.fastener-exit-round')
    assert 0 < result.get_volume() < _exit_volume - 1e-5
    
    assert len(scad.ql.solids().exactly(count=1).resolve(scope=result)) == 1
    return scad.make_part_rpart(part_id='part', body=result, name='three-way-valve-fixture-body')

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
