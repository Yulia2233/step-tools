from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: ruled-l-flange-to-round-nozzle (build, profile=geometry) ----
    flange_sketch = scad.make_sketch_rsketch(name='flange_section', plane={'origin': (0, 0, 0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    flange_sketch = scad.add_point_rsketch(sketch=flange_sketch, point_id='p0', x=-28.0, y=-24.0)
    flange_sketch = scad.add_point_rsketch(sketch=flange_sketch, point_id='p1', x=28.0, y=-24.0)
    flange_sketch = scad.add_point_rsketch(sketch=flange_sketch, point_id='p2', x=28.0, y=-12.0)
    flange_sketch = scad.add_point_rsketch(sketch=flange_sketch, point_id='p3', x=-8.0, y=-12.0)
    flange_sketch = scad.add_point_rsketch(sketch=flange_sketch, point_id='p4', x=-8.0, y=24.0)
    flange_sketch = scad.add_point_rsketch(sketch=flange_sketch, point_id='p5', x=-28.0, y=24.0)
    flange_sketch = scad.add_line_rsketch(sketch=flange_sketch, entity_id='e0', start='p0', end='p1')
    flange_sketch = scad.add_line_rsketch(sketch=flange_sketch, entity_id='e1', start='p1', end='p2')
    flange_sketch = scad.add_line_rsketch(sketch=flange_sketch, entity_id='e2', start='p2', end='p3')
    flange_sketch = scad.add_line_rsketch(sketch=flange_sketch, entity_id='e3', start='p3', end='p4')
    flange_sketch = scad.add_line_rsketch(sketch=flange_sketch, entity_id='e4', start='p4', end='p5')
    flange_sketch = scad.add_line_rsketch(sketch=flange_sketch, entity_id='e5', start='p5', end='p0')
    flange = scad.make_wire_from_sketch_rwire(sketch=flange_sketch)
    outlet_sketch = scad.make_sketch_rsketch(name='outlet_section', plane={'origin': (0, 0, 42.0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    outlet_sketch = scad.add_point_rsketch(sketch=outlet_sketch, point_id='q0', x=10.0, y=0.0)
    outlet_sketch = scad.add_point_rsketch(sketch=outlet_sketch, point_id='q1', x=5.0, y=8.660254)
    outlet_sketch = scad.add_point_rsketch(sketch=outlet_sketch, point_id='q2', x=-5.0, y=8.660254)
    outlet_sketch = scad.add_point_rsketch(sketch=outlet_sketch, point_id='q3', x=-10.0, y=0.0)
    outlet_sketch = scad.add_point_rsketch(sketch=outlet_sketch, point_id='q4', x=-5.0, y=-8.660254)
    outlet_sketch = scad.add_point_rsketch(sketch=outlet_sketch, point_id='q5', x=5.0, y=-8.660254)
    outlet_sketch = scad.add_line_rsketch(sketch=outlet_sketch, entity_id='o0', start='q0', end='q1')
    outlet_sketch = scad.add_line_rsketch(sketch=outlet_sketch, entity_id='o1', start='q1', end='q2')
    outlet_sketch = scad.add_line_rsketch(sketch=outlet_sketch, entity_id='o2', start='q2', end='q3')
    outlet_sketch = scad.add_line_rsketch(sketch=outlet_sketch, entity_id='o3', start='q3', end='q4')
    outlet_sketch = scad.add_line_rsketch(sketch=outlet_sketch, entity_id='o4', start='q4', end='q5')
    outlet_sketch = scad.add_line_rsketch(sketch=outlet_sketch, entity_id='o5', start='q5', end='q0')
    outlet = scad.make_wire_from_sketch_rwire(sketch=outlet_sketch)
    result = scad.loft_rsolid(profiles=[flange, outlet], ruled=True)
    return scad.make_part_rpart(part_id='part', body=result, name='Ruled L flange transition nozzle')

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
