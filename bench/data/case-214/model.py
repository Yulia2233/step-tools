from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: freeform-offset-support-arm (build, profile=geometry) ----
    section = scad.make_sketch_rsketch(name='rectangular_arm_section', plane={'origin': (0, 0, 0), 'x_axis': (0, 1, 0), 'y_axis': (0, 0, 1)})
    section = scad.add_point_rsketch(sketch=section, point_id='a', x=-5.0, y=-3.5)
    section = scad.add_point_rsketch(sketch=section, point_id='b', x=5.0, y=-3.5)
    section = scad.add_point_rsketch(sketch=section, point_id='c', x=5.0, y=3.5)
    section = scad.add_point_rsketch(sketch=section, point_id='d', x=-5.0, y=3.5)
    section = scad.add_line_rsketch(sketch=section, entity_id='ab', start='a', end='b')
    section = scad.add_line_rsketch(sketch=section, entity_id='bc', start='b', end='c')
    section = scad.add_line_rsketch(sketch=section, entity_id='cd', start='c', end='d')
    section = scad.add_line_rsketch(sketch=section, entity_id='da', start='d', end='a')
    profile = scad.make_face_from_sketch_rface(sketch=section)
    rail_edge = scad.make_spline_redge(control_points=[[0, 0, 0], [12, 0, 0], [25, 14, 10], [39, -8, 22], [50, 4, 24]], degree=3, knots=[0.0, 0.5, 1.0], multiplicities=[4, 1, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=False)

    # ---- feature: cylindrical-mounting-boss (add, profile=geometry) ----
    boss = scad.make_cylinder_rsolid(radius=8.0, height=14.0, bottom_face_center=(0, 0, -5), axis=(0, 0, 1))
    result = scad.union_rsolid(result, boss)

    # ---- feature: blind-mounting-socket (subtract, profile=geometry) ----
    socket = scad.make_cylinder_rsolid(radius=3.0, height=6.5, bottom_face_center=(0, 0, 3), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, socket, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Freeform offset support arm with blind mounting socket')

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
