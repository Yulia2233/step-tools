from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: five-station-morphing-support (build, profile=geometry) ----
    profiles = []
    for name, origin, vertices in [
        ('foot', (0.0, 0.0, 0.0), [('a', -11.0, -8.0), ('b', 7.0, -8.0), ('c', 11.0, -3.0), ('d', 11.0, 8.0), ('e', -6.0, 8.0), ('f', -11.0, 3.0)]),
        ('lower', (0.5, 0.0, 10.0), [('a', -10.0, -7.0), ('b', 6.0, -8.0), ('c', 10.0, -2.0), ('d', 8.0, 7.0), ('e', -5.0, 9.0), ('f', -10.0, 4.0)]),
        ('waist', (1.5, 0.5, 20.0), [('a', -8.0, -6.0), ('b', 5.0, -7.0), ('c', 9.0, -1.0), ('d', 6.0, 6.0), ('e', -3.0, 8.0), ('f', -8.0, 3.0)]),
        ('neck', (2.5, 1.0, 30.0), [('a', -7.0, -5.0), ('b', 4.0, -6.0), ('c', 8.0, 0.0), ('d', 4.0, 6.0), ('e', -2.0, 7.0), ('f', -7.0, 2.0)]),
        ('head', (3.0, 1.5, 40.0), [('a', -8.0, -4.0), ('b', 4.0, -5.0), ('c', 9.0, 0.0), ('d', 5.0, 5.0), ('e', -4.0, 6.0), ('f', -9.0, 2.0)]),
    ]:
        section = scad.make_sketch_rsketch(name=name, plane={'origin': origin, 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
        for point_id, x, y in vertices:
            section = scad.add_point_rsketch(sketch=section, point_id=point_id, x=x, y=y)
        for edge_id, start, end in [('ab', 'a', 'b'), ('bc', 'b', 'c'), ('cd', 'c', 'd'), ('de', 'd', 'e'), ('ef', 'e', 'f'), ('fa', 'f', 'a')]:
            section = scad.add_line_rsketch(sketch=section, entity_id=edge_id, start=start, end=end)
        profile = scad.make_wire_from_sketch_rwire(sketch=section)
        profiles.append(profile)
    result = scad.loft_rsolid(profiles=profiles, ruled=False)

    # ---- feature: rectangular-mounting-flange (add, profile=geometry) ----
    flange = scad.make_box_rsolid(width=44.0, height=26.0, depth=5.0, bottom_face_center=(0, 0, -3.0))
    result = scad.union_rsolid(*[result, flange])

    # ---- feature: two-through-bolt-holes (subtract, profile=geometry) ----
    bolt_left = scad.make_cylinder_rsolid(radius=2.2, height=7.0, bottom_face_center=(-17.0, 0, -4.0), axis=(0, 0, 1))
    bolt_right = scad.make_cylinder_rsolid(radius=2.2, height=7.0, bottom_face_center=(17.0, 0, -4.0), axis=(0, 0, 1))
    result = scad.cut_rsolid(*[result, bolt_left, bolt_right], skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Morphing pedestal mounting support')

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
