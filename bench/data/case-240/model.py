from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: seven-section-transition-fairing (build, profile=geometry) ----
    profiles = []
    # Fixed section coordinates intentionally retain free sketch DOF.
    # Rectangle, trapezoids, asymmetric quadrilaterals, and a diamond tip.
    for name, origin, points in [
        ('base', (0, 0, 0), [('a', -22, -15), ('b', 22, -15), ('c', 22, 15), ('d', -22, 15)]),
        ('lower', (0.5, 0, 15), [('a', -21, -14), ('b', 21, -14), ('c', 18, 15), ('d', -18, 15)]),
        ('shoulder', (1.5, 0.5, 30), [('a', -18, -13), ('b', 19, -12), ('c', 14, 16), ('d', -17, 13)]),
        ('waist', (3, 1, 46), [('a', -14, -13), ('b', 17, -9), ('c', 11, 16), ('d', -15, 10)]),
        ('upper', (4.5, 1.5, 62), [('a', -9, -14), ('b', 15, -5), ('c', 7, 16), ('d', -13, 6)]),
        ('neck', (6, 2, 78), [('a', -4, -14), ('b', 13, -2), ('c', 3, 15), ('d', -11, 3)]),
        ('tip', (7, 2, 90), [('a', 0, -13), ('b', 11, 0), ('c', 0, 13), ('d', -10, 0)]),
    ]:
        section = scad.make_sketch_rsketch(name=name, plane={'origin': origin, 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
        for point_id, x, y in points:
            section = scad.add_point_rsketch(sketch=section, point_id=point_id, x=x, y=y)
        section = scad.add_line_rsketch(sketch=section, entity_id='ab', start='a', end='b')
        section = scad.add_line_rsketch(sketch=section, entity_id='bc', start='b', end='c')
        section = scad.add_line_rsketch(sketch=section, entity_id='cd', start='c', end='d')
        section = scad.add_line_rsketch(sketch=section, entity_id='da', start='d', end='a')
        wire = scad.make_wire_from_sketch_rwire(sketch=section)
        profiles.append(wire)
    result = scad.loft_rsolid(profiles=profiles, ruled=False)

    # ---- feature: rectangular-mounting-flange (add, profile=geometry) ----
    flange = scad.make_box_rsolid(width=70, height=44, depth=8, bottom_face_center=(0, 0, -6))
    result = scad.union_rsolid(result, flange)

    # ---- feature: two-through-bolt-holes (subtract, profile=geometry) ----
    left_bolt = scad.make_cylinder_rsolid(radius=3.2, height=12, bottom_face_center=(-28, 0, -8), axis=(0, 0, 1))
    right_bolt = scad.make_cylinder_rsolid(radius=3.2, height=12, bottom_face_center=(28, 0, -8), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, left_bolt, right_bolt, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Seven-section offset instrument fairing')

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
