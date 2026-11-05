from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: rounded-inlet-to-circular-outlet (build, profile=geometry) ----
    inlet_edges = [
        scad.make_line_redge(start=(-22.0, -20.0, 0.0), end=(22.0, -20.0, 0.0)),
        scad.make_three_point_arc_redge(start=(22.0, -20.0, 0.0), middle=(27.657, -17.657, 0.0), end=(30.0, -12.0, 0.0)),
        scad.make_line_redge(start=(30.0, -12.0, 0.0), end=(30.0, 12.0, 0.0)),
        scad.make_three_point_arc_redge(start=(30.0, 12.0, 0.0), middle=(27.657, 17.657, 0.0), end=(22.0, 20.0, 0.0)),
        scad.make_line_redge(start=(22.0, 20.0, 0.0), end=(-22.0, 20.0, 0.0)),
        scad.make_three_point_arc_redge(start=(-22.0, 20.0, 0.0), middle=(-27.657, 17.657, 0.0), end=(-30.0, 12.0, 0.0)),
        scad.make_line_redge(start=(-30.0, 12.0, 0.0), end=(-30.0, -12.0, 0.0)),
        scad.make_three_point_arc_redge(start=(-30.0, -12.0, 0.0), middle=(-27.657, -17.657, 0.0), end=(-22.0, -20.0, 0.0)),
    ]
    inlet = scad.make_wire_from_edges_rwire(edges=inlet_edges)
    outlet = scad.make_circle_rwire(center=(0.0, 0.0, 65.0), radius=12.5, normal=(0.0, 0.0, 1.0))
    result = scad.loft_rsolid(profiles=[inlet, outlet], ruled=True)
    return scad.make_part_rpart(part_id='part', body=result, name='Ruled rounded transition duct')

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
