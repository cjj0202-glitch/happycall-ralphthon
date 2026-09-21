"""Optional, independent static warehouse context; pure data, no Blender or I/O.

All props are behind the sorter/camera-to-parcel region. They have no business
tote identity and never participate in synthetic parcel tracking. Coordinates
are a demonstration design, not a reconstruction of a company facility.
"""
from __future__ import annotations


def environment_specs(name: str) -> dict:
    """Return fresh deterministic specs; 'none' changes no scene geometry."""
    if not isinstance(name, str) or name not in ("none", "staging_v1"):
        raise ValueError("Unknown environment detail; expected 'none' or 'staging_v1'.")
    objects = []
    common = {"synthetic": True, "role": "synthetic-environment", "businessToteId": None,
              "tracked": False, "motion": "static"}

    def cube(label, group, location, dimensions, material, bevel=.005):
        objects.append({**common, "name": "SYN-ENV-" + label, "group": group,
                        "primitive": "cube", "location": list(location), "dimensions": list(dimensions),
                        "material": material, "bevel": bevel})

    def wheel(label, group, location):
        objects.append({**common, "name": "SYN-ENV-" + label, "group": group,
                        "primitive": "cylinder", "location": list(location),
                        "radius": .07, "depth": .06, "axis": "X", "material": "frame"})

    if name == "staging_v1":
        for index, x in enumerate((13.3, 15.1), 1):
            group, y = f"rollcage-{index}", 10.9
            cube(f"CAGE{index}-BASE", group, (x, y, .16), (.9, .8, .04), "steel")
            for side_x in (-1, 1):
                for side_y in (-1, 1):
                    suffix = f"{side_x:+d}-{side_y:+d}"
                    wheel(f"CAGE{index}-WHEEL-{suffix}", group, (x + side_x * .34, y + side_y * .30, .07))
                    cube(f"CAGE{index}-POST-{suffix}", group,
                         (x + side_x * .435, y + side_y * .385, .85), (.03, .03, 1.4), "steel")
            for level, z in enumerate((.75, 1.535), 1):
                for side in (-1, 1):
                    cube(f"CAGE{index}-LONG-RAIL-{level}-{side:+d}", group,
                         (x, y + side * .387, z), (.9, .026, .03), "steel")
                    cube(f"CAGE{index}-END-RAIL-{level}-{side:+d}", group,
                         (x + side * .437, y, z), (.026, .8, .03), "steel")

        for side_x in (-1, 1):
            for side_y in (-1, 1):
                cube(f"RACK-POST-{side_x:+d}-{side_y:+d}", "staging-rack",
                     (18.3 + side_x * 1.77, 12.4 + side_y * .47, .825), (.06, .06, 1.65), "frame")
        for level, top in enumerate((.22, 1.0), 1):
            cube(f"RACK-SHELF-{level}", "staging-rack", (18.3, 12.4, top - .03), (3.6, 1.0, .06), "steel")
            for index, x in enumerate((17.45, 19.15), 1):
                cube(f"STATIC-CARTON-{level}-{index}", "staging-cartons",
                     (x, 12.4, top + .24), (.62, .60, .48), "card", .012)

        # Painted marks are contained in the declared rectangle, not centred
        # on its boundary (which would spill into the reserved safety aisle).
        for index, y in enumerate((10.22, 11.58), 1):
            cube(f"FLOOR-CUE-LONG-{index}", "floor-cue", (14.2, y, .004), (3.6, .04, .008), "yellow", 0)
        for index, x in enumerate((12.42, 15.98), 1):
            cube(f"FLOOR-CUE-END-{index}", "floor-cue", (x, 10.9, .004), (.04, 1.4, .008), "yellow", 0)
    return {"name": name, **common, "geometrySource": "independent-demo-design",
            "notice": "Optional static demonstration context; no actual facility, shipment or tote identity; not tracked.",
            "objects": objects}
