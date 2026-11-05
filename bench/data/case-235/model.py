from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: seven-station-formed-housing (build, profile=geometry) ----
    section_0 = scad.make_wire_from_edges_rwire(edges=[
        scad.make_line_redge(start=(-18, -14, 0), end=(18, -14, 0)),
        scad.make_line_redge(start=(18, -14, 0), end=(18, 14, 0)),
        scad.make_line_redge(start=(18, 14, 0), end=(-18, 14, 0)),
        scad.make_line_redge(start=(-18, 14, 0), end=(-18, -14, 0))])
    section_1 = scad.make_ellipse_rwire(center=(1.5, 0, 8), major_radius=18.0, minor_radius=14.0)
    section_2 = scad.make_wire_from_edges_rwire(edges=[
        scad.make_line_redge(start=(21, 0, 16), end=(12, 13, 16)),
        scad.make_line_redge(start=(12, 13, 16), end=(-7, 15, 16)),
        scad.make_line_redge(start=(-7, 15, 16), end=(-18, 6, 16)),
        scad.make_line_redge(start=(-18, 6, 16), end=(-16, -9, 16)),
        scad.make_line_redge(start=(-16, -9, 16), end=(-2, -15, 16)),
        scad.make_line_redge(start=(-2, -15, 16), end=(14, -12, 16)),
        scad.make_line_redge(start=(14, -12, 16), end=(21, 0, 16))])
    section_3 = scad.make_circle_rwire(center=(3, -1, 24), radius=15.0)
    section_4 = scad.make_wire_from_edges_rwire(edges=[
        scad.make_line_redge(start=(-10, -12, 32), end=(17, -12, 32)),
        scad.make_line_redge(start=(17, -12, 32), end=(17, 10, 32)),
        scad.make_line_redge(start=(17, 10, 32), end=(-10, 10, 32)),
        scad.make_line_redge(start=(-10, 10, 32), end=(-10, -12, 32))])
    section_5 = scad.make_ellipse_rwire(center=(0, 1, 40), major_radius=12.0, minor_radius=9.5)
    section_6 = scad.make_circle_rwire(center=(-1.5, 0, 48), radius=9.0)
    result = scad.loft_rsolid(profiles=[section_0, section_1, section_2, section_3, section_4, section_5, section_6], ruled=False)

    # ---- feature: axial-clearance-bore (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=3.2, height=54.0, bottom_face_center=(0, 0, -2), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bore, skip_non_intersecting=False)
    return scad.make_part_rpart(part_id='part', body=result, name='Seven-station formed duct housing')

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
