from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: six-station-noncongruent-loft (build, profile=geometry) ----
    section_0 = scad.make_polyline_rwire(points=[(-11.0, -7.0, 0.0), (7.0, -9.0, 0.0), (12.0, 1.0, 0.0), (4.0, 12.0, 0.0), (-10.0, 8.0, 0.0)], closed=True)
    section_1 = scad.make_polyline_rwire(points=[(-8.0, -12.0, 9.0), (6.0, -11.0, 9.0), (13.0, -2.0, 9.0), (10.0, 9.0, 9.0), (-2.0, 13.0, 9.0), (-12.0, 5.0, 9.0)], closed=True)
    section_2 = scad.make_polyline_rwire(points=[(-5.0, -13.0, 18.0), (8.0, -12.0, 18.0), (15.0, -5.0, 18.0), (14.0, 6.0, 18.0), (6.0, 14.0, 18.0), (-7.0, 12.0, 18.0), (-14.0, 3.0, 18.0)], closed=True)
    section_3 = scad.make_polyline_rwire(points=[(-1.0, -14.0, 28.0), (9.0, -12.0, 28.0), (16.0, -7.0, 28.0), (17.0, 2.0, 28.0), (12.0, 10.0, 28.0), (4.0, 15.0, 28.0), (-6.0, 13.0, 28.0), (-14.0, 7.0, 28.0)], closed=True)
    section_4 = scad.make_polyline_rwire(points=[(2.0, -12.0, 39.0), (13.0, -8.0, 39.0), (16.0, 3.0, 39.0), (8.0, 13.0, 39.0), (-5.0, 11.0, 39.0), (-12.0, 0.0, 39.0)], closed=True)
    section_5 = scad.make_polyline_rwire(points=[(4.0, -9.0, 50.0), (14.0, -4.0, 50.0), (13.0, 7.0, 50.0), (1.0, 12.0, 50.0), (-8.0, 3.0, 50.0)], closed=True)
    result = scad.loft_rsolid(profiles=[section_0, section_1, section_2, section_3, section_4, section_5], ruled=False)

    # ---- feature: axial-through-bore (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=3.2, height=52.0, bottom_face_center=(0.0, 0.0, -1.0), axis=(0.0, 0.0, 1.0))
    result = scad.cut_rsolid(result, bore, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Noncongruent lofted duct handle')

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
