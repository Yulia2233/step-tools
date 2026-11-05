from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: rectangular-inlet-section (build, profile=geometry) ----
    inlet_sketch = scad.make_sketch_rsketch(name='rectangular_inlet', plane='XY')
    inlet_sketch = scad.add_point_rsketch(sketch=inlet_sketch, point_id='a', x=-32.0, y=-22.0)
    inlet_sketch = scad.add_point_rsketch(sketch=inlet_sketch, point_id='b', x=32.0, y=-22.0)
    inlet_sketch = scad.add_point_rsketch(sketch=inlet_sketch, point_id='c', x=32.0, y=22.0)
    inlet_sketch = scad.add_point_rsketch(sketch=inlet_sketch, point_id='d', x=-32.0, y=22.0)
    inlet_sketch = scad.add_line_rsketch(sketch=inlet_sketch, entity_id='ab', start='a', end='b')
    inlet_sketch = scad.add_line_rsketch(sketch=inlet_sketch, entity_id='bc', start='b', end='c')
    inlet_sketch = scad.add_line_rsketch(sketch=inlet_sketch, entity_id='cd', start='c', end='d')
    inlet_sketch = scad.add_line_rsketch(sketch=inlet_sketch, entity_id='da', start='d', end='a')
    inlet = scad.make_wire_from_sketch_rwire(sketch=inlet_sketch)

    # ---- feature: round-outlet-section (build, profile=geometry) ----
    outlet_sketch = scad.make_sketch_rsketch(name='round_outlet', plane={'origin': (0, 0, 100.0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    outlet_sketch = scad.add_point_rsketch(sketch=outlet_sketch, point_id='center', x=0.0, y=0.0)
    outlet_sketch = scad.add_circle_rsketch(sketch=outlet_sketch, entity_id='rim', center='center', radius=18.0)
    outlet = scad.make_wire_from_sketch_rwire(sketch=outlet_sketch)

    # ---- feature: ruled-cable-guide-transition (build, profile=geometry) ----
    result = scad.loft_rsolid(profiles=[inlet, outlet], ruled=True)

    # ---- feature: axial-cable-passage (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=10.0, height=104.0, bottom_face_center=(0, 0, -2.0), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bore, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Ruled rectangular-to-round cable guide')

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
