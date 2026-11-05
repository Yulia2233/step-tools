from pathlib import Path

import simplecadapi as scad
from simplecadapi import ql


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: oval-grip-section (build, profile=geometry) ----
    quadrant_a = scad.make_spline_redge(control_points=[[9, 0, 0], [9, 3.3137085, 0], [4.97056275, 6, 0], [0, 6, 0]], degree=3, knots=[0, 1], multiplicities=[4, 4])
    quadrant_b = scad.make_spline_redge(control_points=[[0, 6, 0], [-4.97056275, 6, 0], [-9, 3.3137085, 0], [-9, 0, 0]], degree=3, knots=[0, 1], multiplicities=[4, 4])
    quadrant_c = scad.make_spline_redge(control_points=[[-9, 0, 0], [-9, -3.3137085, 0], [-4.97056275, -6, 0], [0, -6, 0]], degree=3, knots=[0, 1], multiplicities=[4, 4])
    quadrant_d = scad.make_spline_redge(control_points=[[0, -6, 0], [4.97056275, -6, 0], [9, -3.3137085, 0], [9, 0, 0]], degree=3, knots=[0, 1], multiplicities=[4, 4])
    section_wire = scad.make_wire_from_edges_rwire(edges=[quadrant_a, quadrant_b, quadrant_c, quadrant_d])
    section = scad.make_face_from_wire_rface(wire=section_wire, normal=(0, 0, 1))

    # ---- feature: spatial-grip-sweep (build, profile=geometry) ----
    rail_edge = scad.make_spline_redge(control_points=[[0, 0, 0], [0, 0, 18], [14, 6, 38], [26, -10, 60], [18, 10, 80], [12, 20, 96]], degree=3, knots=[0, 0.3333333333, 0.6666666667, 1], multiplicities=[4, 1, 1, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    result = scad.sweep_rsolid(profile=section, path=rail, is_frenet=True)

    # ---- feature: soft-end-rims (fillet, profile=geometry) ----
    caps = ql.faces().where(ql.prop('geom.type', '==', 'PLANE'))
    rims = caps.boundary(to_kind='edge').exactly(8)
    print('Selected end-rim edges:', len(rims.resolve(result)))
    result = scad.fillet_rsolid(solid=result, edges=rims, radius=0.8)

    return scad.make_part_rpart(part_id='part', body=result, name='Spatial curved oval instrument grip')

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
