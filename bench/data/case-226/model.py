from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: rounded-grip-section (build, profile=geometry) ----
    edges = []
    edges.append(scad.make_line_redge(start=(0, -2.5, -3), end=(0, 2.5, -3)))
    edges.append(scad.make_three_point_arc_redge(start=(0, 2.5, -3), middle=(0, 3.5606601718, -2.5606601718), end=(0, 4, -1.5)))
    edges.append(scad.make_line_redge(start=(0, 4, -1.5), end=(0, 4, 1.5)))
    edges.append(scad.make_three_point_arc_redge(start=(0, 4, 1.5), middle=(0, 3.5606601718, 2.5606601718), end=(0, 2.5, 3)))
    edges.append(scad.make_line_redge(start=(0, 2.5, 3), end=(0, -2.5, 3)))
    edges.append(scad.make_three_point_arc_redge(start=(0, -2.5, 3), middle=(0, -3.5606601718, 2.5606601718), end=(0, -4, 1.5)))
    edges.append(scad.make_line_redge(start=(0, -4, 1.5), end=(0, -4, -1.5)))
    edges.append(scad.make_three_point_arc_redge(start=(0, -4, -1.5), middle=(0, -3.5606601718, -2.5606601718), end=(0, -2.5, -3)))
    section_wire = scad.make_wire_from_edges_rwire(edges=edges)
    section = scad.make_face_from_wire_rface(wire=section_wire, normal=(1, 0, 0))

    # ---- feature: mixed-rail-swept-grip (build, profile=geometry) ----
    straight = scad.make_line_redge(start=(0, 0, 0), end=(10, 0, 0))
    curved = scad.make_spline_redge(control_points=[(10, 0, 0), (22, 0, 0), (27, 12, 0), (40, 14, 0)], degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[straight, curved])
    result = scad.sweep_rsolid(profile=section, path=rail, is_frenet=True)

    # ---- feature: mounting-boss (add, profile=geometry) ----
    boss = scad.make_cylinder_rsolid(radius=5.5, height=8.0, bottom_face_center=(5, 0, -2), axis=(0, 0, 1))
    result = scad.union_rsolid(result, boss)

    # ---- feature: blind-mounting-bore (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=2.2, height=5.5, bottom_face_center=(5, 0, 1.5), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bore, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Curved instrument grip with blind mounting boss')

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
