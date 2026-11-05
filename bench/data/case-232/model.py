from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: six-station-transition-grip (build, profile=geometry) ----
    profiles = []
    # L-shaped heel progressively becomes a compact hexagonal grip end.
    # Each station changes both proportions and polygon corner geometry.
    for station, origin, points in [
        ('heel', (0, 0, 0), [('a', -20, -16), ('b', 20, -16), ('c', 20, -3), ('d', 3, -3), ('e', 3, 16), ('f', -20, 16)]),
        ('lower', (0.8, -0.4, 14), [('a', -19, -15), ('b', 19, -15), ('c', 20, -2), ('d', 5, 0), ('e', 4, 16), ('f', -19, 15)]),
        ('palm', (1.8, -0.8, 30), [('a', -17, -14), ('b', 17, -14), ('c', 19, -1), ('d', 9, 5), ('e', 3, 15), ('f', -18, 13)]),
        ('waist', (2.6, -0.5, 47), [('a', -15, -12), ('b', 14, -12), ('c', 17, 0), ('d', 12, 9), ('e', 1, 14), ('f', -17, 10)]),
        ('upper', (3.2, 0.2, 64), [('a', -14, -11), ('b', 12, -11), ('c', 16, -1), ('d', 11, 11), ('e', -1, 14), ('f', -16, 7)]),
        ('tip', (3.5, 0.8, 80), [('a', -13, -10), ('b', 10, -10), ('c', 15, -2), ('d', 10, 10), ('e', -3, 13), ('f', -15, 5)]),
    ]:
        section = scad.make_sketch_rsketch(name=station, plane={'origin': origin, 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
        for point_id, x, y in points:
            section = scad.add_point_rsketch(sketch=section, point_id=point_id, x=x, y=y)
        for entity_id, start, end in [('ab', 'a', 'b'), ('bc', 'b', 'c'), ('cd', 'c', 'd'), ('de', 'd', 'e'), ('ef', 'e', 'f'), ('fa', 'f', 'a')]:
            section = scad.add_line_rsketch(sketch=section, entity_id=entity_id, start=start, end=end)
        profile = scad.make_wire_from_sketch_rwire(sketch=section)
        profiles.append(profile)
    result = scad.loft_rsolid(profiles=profiles, ruled=False)

    # ---- feature: axial-shaft-through-bore (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=4.0, height=84.0, bottom_face_center=(-6, -3, -2), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bore, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Noncongruent lofted transition grip')

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
