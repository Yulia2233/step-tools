from pathlib import Path
import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: mounting-stock (build, profile=geometry) ----
    result = scad.make_box_rsolid(width=86.0, height=64.0, depth=10.0, bottom_face_center=(0.0, 0.0, 0.0))
    
    # ---- feature: ql-top-perimeter-bevel (modify, profile=geometry) ----
    rim = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='LINE')).where(predicate=scad.ql.prop(path='geom.center.z', op='>', value_=9.999)).exactly(count=4).resolve(scope=result))
    _rim_volume = result.get_volume()
    result = scad.chamfer_rsolid(solid=result, edges=rim, distance=0.7, generated_faces_tag='feature.mount-rim-bevel')
    assert 0 < result.get_volume() < _rim_volume - 1e-5
    
    # ---- feature: ql-bottom-perimeter-round (modify, profile=geometry) ----
    bottom_edges = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='LINE')).where(predicate=scad.ql.prop(path='geom.center.z', op='<', value_=0.001)).exactly(count=4).resolve(scope=result))
    result = scad.fillet_rsolid(solid=result, edges=bottom_edges, radius=0.5, generated_faces_tag='feature.mount-bottom-round')
    
    # ---- feature: rear-instrument-upright (add, profile=geometry) ----
    upright = scad.make_box_rsolid(width=66.0, height=11.0, depth=34.0, bottom_face_center=(0.0, 16.0, 9.0))
    _volume_before_1 = result.get_volume()
    result = scad.union_rsolid(result, upright)
    assert result.get_volume() > _volume_before_1 + 1e-5, "additive feature must add volume"
    
    # ---- feature: triangular-load-path-gussets (add, profile=geometry) ----
    gusset_0_sketch = scad.make_sketch_rsketch(name='gusset_0', plane={'origin': (-27.0, 0.0, 0.0), 'x_axis': (0.0, 1.0, 0.0), 'y_axis': (0.0, 0.0, 1.0)})
    gusset_0_sketch = scad.add_point_rsketch(sketch=gusset_0_sketch, point_id='p0', x=-13.0, y=9.0)
    gusset_0_sketch = scad.add_point_rsketch(sketch=gusset_0_sketch, point_id='p1', x=15.0, y=9.0)
    gusset_0_sketch = scad.add_point_rsketch(sketch=gusset_0_sketch, point_id='p2', x=15.0, y=35.0)
    gusset_0_sketch = scad.add_line_rsketch(sketch=gusset_0_sketch, entity_id='e0', start='p0', end='p1')
    gusset_0_sketch = scad.add_line_rsketch(sketch=gusset_0_sketch, entity_id='e1', start='p1', end='p2')
    gusset_0_sketch = scad.add_line_rsketch(sketch=gusset_0_sketch, entity_id='e2', start='p2', end='p0')
    gusset_0_profile = scad.make_face_from_sketch_rface(sketch=gusset_0_sketch, profile='e0')
    gusset_0 = scad.extrude_rsolid(profile=gusset_0_profile, direction=(1.0, 0.0, 0.0), distance=6.0)
    _volume_before_2 = result.get_volume()
    result = scad.union_rsolid(result, gusset_0)
    assert result.get_volume() > _volume_before_2 + 1e-5, "additive feature must add volume"
    gusset_1_sketch = scad.make_sketch_rsketch(name='gusset_1', plane={'origin': (21.0, 0.0, 0.0), 'x_axis': (0.0, 1.0, 0.0), 'y_axis': (0.0, 0.0, 1.0)})
    gusset_1_sketch = scad.add_point_rsketch(sketch=gusset_1_sketch, point_id='p0', x=-13.0, y=9.0)
    gusset_1_sketch = scad.add_point_rsketch(sketch=gusset_1_sketch, point_id='p1', x=15.0, y=9.0)
    gusset_1_sketch = scad.add_point_rsketch(sketch=gusset_1_sketch, point_id='p2', x=15.0, y=35.0)
    gusset_1_sketch = scad.add_line_rsketch(sketch=gusset_1_sketch, entity_id='e0', start='p0', end='p1')
    gusset_1_sketch = scad.add_line_rsketch(sketch=gusset_1_sketch, entity_id='e1', start='p1', end='p2')
    gusset_1_sketch = scad.add_line_rsketch(sketch=gusset_1_sketch, entity_id='e2', start='p2', end='p0')
    gusset_1_profile = scad.make_face_from_sketch_rface(sketch=gusset_1_sketch, profile='e0')
    gusset_1 = scad.extrude_rsolid(profile=gusset_1_profile, direction=(1.0, 0.0, 0.0), distance=6.0)
    _volume_before_3 = result.get_volume()
    result = scad.union_rsolid(result, gusset_1)
    assert result.get_volume() > _volume_before_3 + 1e-5, "additive feature must add volume"
    
    # ---- feature: instrument-fixing-pair (subtract, profile=geometry) ----
    instrument_0 = scad.make_cylinder_rsolid(radius=3.0, height=15.0, bottom_face_center=(-13.0, 9.0, 29.0), axis=(0.0, 1.0, 0.0))
    _volume_before_4 = result.get_volume()
    result = scad.cut_rsolid(result, instrument_0, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_4 - 1e-5, "subtractive feature must remove volume"
    instrument_1 = scad.make_cylinder_rsolid(radius=3.0, height=15.0, bottom_face_center=(13.0, 9.0, 29.0), axis=(0.0, 1.0, 0.0))
    _volume_before_5 = result.get_volume()
    result = scad.cut_rsolid(result, instrument_1, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_5 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: upright-wiring-window (subtract, profile=geometry) ----
    wire_window = scad.make_box_rsolid(width=12.0, height=15.0, depth=7.0, bottom_face_center=(0.0, 16.0, 21.0))
    _volume_before_6 = result.get_volume()
    result = scad.cut_rsolid(result, wire_window, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_6 - 1e-5, "subtractive feature must remove volume"
    
    # ---- feature: elongated-fastening-slots (subtract, profile=geometry) ----
    slot_end_0a = scad.make_cylinder_rsolid(radius=2.6, height=12.0, bottom_face_center=(-35.0, -5.0, -1.0), axis=(0.0, 0.0, 1.0))
    slot_end_0b = scad.make_cylinder_rsolid(radius=2.6, height=12.0, bottom_face_center=(-35.0, 5.0, -1.0), axis=(0.0, 0.0, 1.0))
    slot_mid_0 = scad.make_box_rsolid(width=5.2, height=10.0, depth=12.0, bottom_face_center=(-35.0, 0.0, -1.0))
    slot_tool_0 = scad.union_rsolid(slot_end_0a, slot_mid_0, slot_end_0b)
    _volume_before_7 = result.get_volume()
    result = scad.cut_rsolid(result, slot_tool_0, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_7 - 1e-5, "subtractive feature must remove volume"
    slot_end_1a = scad.make_cylinder_rsolid(radius=2.6, height=12.0, bottom_face_center=(35.0, -5.0, -1.0), axis=(0.0, 0.0, 1.0))
    slot_end_1b = scad.make_cylinder_rsolid(radius=2.6, height=12.0, bottom_face_center=(35.0, 5.0, -1.0), axis=(0.0, 0.0, 1.0))
    slot_mid_1 = scad.make_box_rsolid(width=5.2, height=10.0, depth=12.0, bottom_face_center=(35.0, 0.0, -1.0))
    slot_tool_1 = scad.union_rsolid(slot_end_1a, slot_mid_1, slot_end_1b)
    _volume_before_8 = result.get_volume()
    result = scad.cut_rsolid(result, slot_tool_1, skip_non_intersecting=False)
    assert 0 < result.get_volume() < _volume_before_8 - 1e-5, "subtractive feature must remove volume"
    
    assert len(scad.ql.solids().exactly(count=1).resolve(scope=result)) == 1
    return scad.make_part_rpart(part_id='part', body=result, name='gusseted-offset-instrument-bracket')

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
