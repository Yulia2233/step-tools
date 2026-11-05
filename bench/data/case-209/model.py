from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: freeform-swept-grip (build, profile=geometry) ----
    rail_edge = scad.make_spline_redge(control_points=[[-18.0, 0.0, 0.0], [-7.0, 8.0, 4.0], [7.0, -6.0, 5.0], [18.0, 0.0, 0.0]], degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    profile = scad.make_rectangle_rface(width=6.0, height=9.0, center=(-18.0, 0.0, 0.0), normal=(1.0, 0.0, 0.0))
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Freeform swept grip')

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
