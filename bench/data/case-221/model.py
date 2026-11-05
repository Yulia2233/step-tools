from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: swept-spline-handle (build, profile=geometry) ----
    rail_edge = scad.make_spline_redge(
        control_points=[[-20.0, 0.0, 0.0], [-14.0, 0.0, 0.0], [-8.0, 8.0, 0.0], [-2.0, 8.0, 0.0], [4.0, -8.0, 0.0], [12.0, -8.0, 0.0], [20.0, 0.0, 0.0]],
        degree=3,
        knots=[0.0, 0.25, 0.5, 0.75, 1.0],
        multiplicities=[4, 1, 1, 1, 4],
    )
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    profile_edge = scad.make_spline_redge(
        control_points=[[-20.0, 0.0, 2.0], [-20.0, 1.4, 1.4], [-20.0, 2.0, 0.0], [-20.0, 1.4, -1.4], [-20.0, 0.0, -2.0], [-20.0, -1.4, -1.4], [-20.0, -2.0, 0.0], [-20.0, -1.4, 1.4]],
        degree=3,
        periodic=True,
    )
    profile_wire = scad.make_wire_from_edges_rwire(edges=[profile_edge])
    profile = scad.make_face_from_wire_rface(wire=profile_wire, normal=(-1, 0, 0))
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=True)
    return scad.make_part_rpart(part_id='part', body=result, name='S-curve spline handle')

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
