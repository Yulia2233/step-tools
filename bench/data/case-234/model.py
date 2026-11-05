from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: six-section-offset-transition-grip (build, profile=geometry) ----
    profiles = []
    for name, origin, points in [
        ('heel', (0, 0, 0), [('a', -22, -13), ('b', 14, -13), ('c', 22, -5), ('d', 22, 11), ('e', -13, 11), ('f', -22, 2)]),
        ('lower', (1, 0.5, 14), [('a', -20, -12), ('b', 13, -12), ('c', 20, -6), ('d', 19, 11), ('e', -12, 12), ('f', -21, 3)]),
        ('waist', (3, 1, 30), [('a', -15, -10), ('b', 10, -11), ('c', 16, -5), ('d', 15, 10), ('e', -9, 12), ('f', -17, 4)]),
        ('palm', (5, 2, 47), [('a', -14, -11), ('b', 12, -12), ('c', 19, -4), ('d', 17, 12), ('e', -8, 14), ('f', -17, 5)]),
        ('upper', (6, 2.5, 64), [('a', -17, -12), ('b', 14, -11), ('c', 20, -3), ('d', 19, 13), ('e', -10, 13), ('f', -19, 5)]),
        ('crown', (5, 2, 80), [('a', -18, -11), ('b', 12, -11), ('c', 18, -5), ('d', 18, 10), ('e', -10, 10), ('f', -18, 2)]),
    ]:
        section = scad.make_sketch_rsketch(name=name, plane={'origin': origin, 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
        for point_id, x, y in points:
            section = scad.add_point_rsketch(sketch=section, point_id=point_id, x=x, y=y)
        for entity_id, start, end in [('ab', 'a', 'b'), ('bc', 'b', 'c'), ('cd', 'c', 'd'), ('de', 'd', 'e'), ('ef', 'e', 'f'), ('fa', 'f', 'a')]:
            section = scad.add_line_rsketch(sketch=section, entity_id=entity_id, start=start, end=end)
        profiles.append(scad.make_wire_from_sketch_rwire(sketch=section))
    result = scad.loft_rsolid(profiles=profiles, ruled=False)

    # ---- feature: crown-long-edge-breaks (modify, profile=geometry) ----
    crown_edges = scad.ql.edges().where(predicate=scad.ql.prop(path='geom.center.z', op='>=', value_=79.99))
    crown_edges = crown_edges.where(predicate=scad.ql.prop(path='geom.center.z', op='<=', value_=80.01))
    crown_edges = crown_edges.where(predicate=scad.ql.prop(path='geom.length', op='>', value_=25.0))
    print('Crown chamfer edges:', len(crown_edges.resolve(scope=result)))
    result = scad.chamfer_rsolid(solid=result, edges=crown_edges.exactly(count=2), distance=0.7)

    return scad.make_part_rpart(part_id='part', body=result, name='Offset sculpted transition grip')

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
