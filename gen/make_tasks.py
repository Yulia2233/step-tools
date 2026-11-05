#!/usr/bin/env python3
"""Task list for the extra benchmark parts: the free-form operations the 200-part benchmark lacks."""
import json
import random

rng = random.Random(20261105)
PROFILES = ["a circle", "a rectangle", "a rounded rectangle (four lines and four arcs)", "an ellipse-like closed spline", "an L-shaped polygon", "a hexagon"]
FINISH = [
    "union a rectangular mounting flange at one end and cut two bolt holes through it",
    "cut a through-hole along the part with a cylinder tool",
    "fillet a few sharp edges selected with QL predicates",
    "chamfer a few sharp edges selected with QL predicates",
    "union a cylindrical boss and cut a blind hole in it",
    "no extra feature: the free-form body alone",
]
KINDS = [
    ("sweep_spline", 14, "SWEEP one closed planar profile ({prof}) along a RAIL that is a smooth spline wire through {n} 3D control points that are NOT coplanar (a free-form curved rail), using `scad.make_spline_redge` for the rail and `scad.sweep_rsolid`; is_frenet={fr}. The swept side surface must be a genuinely free-form (B-spline) surface, not a cylinder or torus."),
    ("sweep_planar_spline", 8, "SWEEP one closed planar profile ({prof}) along a planar S-shaped spline rail (made with `scad.make_spline_redge`, {n} control points in one plane) using `scad.sweep_rsolid`; is_frenet={fr}. The swept side surface must be free-form."),
    ("sweep_mixed_rail", 8, "SWEEP one closed planar profile ({prof}) along a rail wire made of a straight line followed by a spline edge (join them into one wire), using `scad.sweep_rsolid`; is_frenet={fr}. The spline part of the swept surface must be free-form."),
    ("loft_noncongruent", 12, "LOFT through {n} planar section wires of DIFFERENT shapes and sizes (for example {prof} changing into something else), stacked at different heights and slightly offset sideways, `scad.loft_rsolid(..., ruled=False)`. The sections must not be congruent copies of each other."),
    ("loft_ruled", 6, "RULED loft (`ruled=True`) between two or three planar section wires of different shape ({prof} to another polygon or circle), using `scad.loft_rsolid`."),
    ("revolve_spline", 8, "REVOLVE a closed profile that contains at least one spline edge (a free-form meridian made with `scad.make_spline_redge` inside a wire, closed with straight lines on the axis side) around an axis with `scad.revolve_rsolid`, 360 degrees. The result must contain a free-form surface of revolution, not just cones and cylinders."),
    ("extrude_spline", 4, "EXTRUDE a closed profile whose outline contains spline edges (built with `scad.make_spline_redge` inside a wire) straight along a direction with `scad.extrude_rsolid`; the side surface must be free-form."),
]


def main():
    tasks, k = [], 0
    for kind, count, text in KINDS:
        for _ in range(count):
            k += 1
            spec = text.format(prof=rng.choice(PROFILES), n=rng.choice([4, 5, 6, 7]), fr=rng.choice(["False", "True"]))
            fin = rng.choice(FINISH)
            size = rng.choice([30, 45, 60, 80, 100])
            tasks.append({"id": f"x{k:03d}", "kind": kind, "spec": spec, "finish": fin, "size_mm": size, "seed": rng.randrange(10**6)})
    json.dump(tasks, open("tasks.json", "w"), indent=1)
    print(len(tasks), "tasks")


if __name__ == "__main__":
    main()
