from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: revolved-freeform-housing (build, profile=geometry) ----
    meridian_curve = scad.make_spline_redge(control_points=[[24.0, 0.0, -32.0], [36.0, 0.0, -24.0], [40.0, 0.0, -8.0], [39.0, 0.0, 10.0], [34.0, 0.0, 24.0], [27.0, 0.0, 32.0]], degree=3, knots=[0.0, 0.33, 0.66, 1.0], multiplicities=[4, 1, 1, 4])
    meridian_top = scad.make_segment_redge(start=(27.0, 0.0, 32.0), end=(0.0, 0.0, 32.0))
    meridian_axis = scad.make_segment_redge(start=(0.0, 0.0, 32.0), end=(0.0, 0.0, -32.0))
    meridian_bottom = scad.make_segment_redge(start=(0.0, 0.0, -32.0), end=(24.0, 0.0, -32.0))
    meridian_profile = scad.make_wire_from_edges_rwire(edges=[meridian_curve, meridian_top, meridian_axis, meridian_bottom])
    result = scad.revolve_rsolid(profile=meridian_profile, axis=(0.0, 0.0, 1.0), angle=360.0, origin=(0.0, 0.0, 0.0))

    # ---- feature: top-service-boss (add, profile=geometry) ----
    boss = scad.make_cylinder_rsolid(radius=9.0, height=8.0, bottom_face_center=(0.0, 0.0, 30.0), axis=(0.0, 0.0, 1.0))
    result = scad.union_rsolid(result, boss)

    # ---- feature: blind-boss-bore (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=3.5, height=6.0, bottom_face_center=(0.0, 0.0, 32.0), axis=(0.0, 0.0, 1.0))
    result = scad.cut_rsolid(result, bore, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Freeform revolved service housing')

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
