from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: five-station-transition-shell (build, profile=geometry) ----
    section_0 = scad.make_sketch_rsketch(name='section_0', plane={'origin': (-2.0, 0.0, 0.0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    for point_id, x, y in [('a', -10.0, -7.0), ('b', 8.0, -7.0), ('c', 10.0, 5.0), ('d', -8.0, 7.0)]:
        section_0 = scad.add_point_rsketch(sketch=section_0, point_id=point_id, x=x, y=y)
    for edge_id, start, end in [('ab', 'a', 'b'), ('bc', 'b', 'c'), ('cd', 'c', 'd'), ('da', 'd', 'a')]:
        section_0 = scad.add_line_rsketch(sketch=section_0, entity_id=edge_id, start=start, end=end)
    wire_0 = scad.make_wire_from_sketch_rwire(sketch=section_0)

    section_1 = scad.make_sketch_rsketch(name='section_1', plane={'origin': (-1.0, 0.5, 10.0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    for point_id, x, y in [('a', -8.0, -9.0), ('b', 8.0, -6.0), ('c', 8.0, 7.0), ('d', -7.0, 8.0)]:
        section_1 = scad.add_point_rsketch(sketch=section_1, point_id=point_id, x=x, y=y)
    for edge_id, start, end in [('ab', 'a', 'b'), ('bc', 'b', 'c'), ('cd', 'c', 'd'), ('da', 'd', 'a')]:
        section_1 = scad.add_line_rsketch(sketch=section_1, entity_id=edge_id, start=start, end=end)
    wire_1 = scad.make_wire_from_sketch_rwire(sketch=section_1)

    section_2 = scad.make_sketch_rsketch(name='section_2', plane={'origin': (1.0, 1.0, 21.0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    for point_id, x, y in [('a', -7.0, -7.0), ('b', 7.0, -7.0), ('c', 7.0, 7.0), ('d', -7.0, 7.0)]:
        section_2 = scad.add_point_rsketch(sketch=section_2, point_id=point_id, x=x, y=y)
    for edge_id, start, end in [('ab', 'a', 'b'), ('bc', 'b', 'c'), ('cd', 'c', 'd'), ('da', 'd', 'a')]:
        section_2 = scad.add_line_rsketch(sketch=section_2, entity_id=edge_id, start=start, end=end)
    wire_2 = scad.make_wire_from_sketch_rwire(sketch=section_2)

    section_3 = scad.make_sketch_rsketch(name='section_3', plane={'origin': (2.0, 0.5, 32.0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    for point_id, x, y in [('a', -6.0, -6.0), ('b', 5.0, -8.0), ('c', 7.0, 5.0), ('d', -5.0, 7.0)]:
        section_3 = scad.add_point_rsketch(sketch=section_3, point_id=point_id, x=x, y=y)
    for edge_id, start, end in [('ab', 'a', 'b'), ('bc', 'b', 'c'), ('cd', 'c', 'd'), ('da', 'd', 'a')]:
        section_3 = scad.add_line_rsketch(sketch=section_3, entity_id=edge_id, start=start, end=end)
    wire_3 = scad.make_wire_from_sketch_rwire(sketch=section_3)

    section_4 = scad.make_sketch_rsketch(name='section_4', plane={'origin': (3.0, 0.0, 43.0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    for point_id, x, y in [('a', -4.0, -5.0), ('b', 4.0, -5.0), ('c', 5.0, 4.0), ('d', -3.0, 5.0)]:
        section_4 = scad.add_point_rsketch(sketch=section_4, point_id=point_id, x=x, y=y)
    for edge_id, start, end in [('ab', 'a', 'b'), ('bc', 'b', 'c'), ('cd', 'c', 'd'), ('da', 'd', 'a')]:
        section_4 = scad.add_line_rsketch(sketch=section_4, entity_id=edge_id, start=start, end=end)
    wire_4 = scad.make_wire_from_sketch_rwire(sketch=section_4)
    result = scad.loft_rsolid(profiles=[wire_0, wire_1, wire_2, wire_3, wire_4], ruled=False)

    # ---- feature: axial-through-bore (subtract, profile=geometry) ----
    bore_tool = scad.make_cylinder_rsolid(radius=2.5, height=47.0, bottom_face_center=(0.0, 0.0, -2.0), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bore_tool, skip_non_intersecting=False)
    return scad.make_part_rpart(part_id='part', body=result, name='Five-station lofted transition handle')

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
