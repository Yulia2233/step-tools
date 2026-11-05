from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: seven-station-handle-body (build, profile=geometry) ----
    section_0 = scad.make_circle_rwire(center=(-1.5, 0.0, 0.0), radius=11.0, normal=(0, 0, 1))
    section_1 = scad.make_ellipse_rwire(center=(-0.8, 0.4, 6.5), major_radius=15.0, minor_radius=10.5, normal=(0, 0, 1), major_direction=(1, 0, 0))
    section_2 = scad.make_circle_rwire(center=(0.0, 1.0, 13.0), radius=16.5, normal=(0, 0, 1))
    section_3 = scad.make_ellipse_rwire(center=(0.8, 1.7, 20.0), major_radius=18.5, minor_radius=13.0, normal=(0, 0, 1), major_direction=(1, 0, 0))
    section_4 = scad.make_circle_rwire(center=(1.6, 2.0, 27.0), radius=17.0, normal=(0, 0, 1))
    section_5 = scad.make_ellipse_rwire(center=(2.2, 1.0, 34.5), major_radius=15.0, minor_radius=11.0, normal=(0, 0, 1), major_direction=(1, 0, 0))
    section_6 = scad.make_circle_rwire(center=(2.8, 0.0, 42.0), radius=10.0, normal=(0, 0, 1))
    result = scad.loft_rsolid(profiles=[section_0, section_1, section_2, section_3, section_4, section_5, section_6], ruled=False)

    # ---- feature: mounting-collar (add, profile=geometry) ----
    collar = scad.make_cylinder_rsolid(radius=12.5, height=4.0, bottom_face_center=(-1.5, 0.0, -1.0), axis=(0, 0, 1))
    result = scad.union_rsolid(result, collar)

    # ---- feature: soften-end-rims (modify, profile=geometry) ----
    rim_edges = scad.ql.edges().where(scad.ql.prop("geom.center.z", "<", -0.9)).take(1).exactly(1)
    result = scad.fillet_rsolid(solid=result, edges=rim_edges, radius=0.4)

    return scad.make_part_rpart(part_id='part', body=result, name='Seven-station ergonomic loft handle')

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
