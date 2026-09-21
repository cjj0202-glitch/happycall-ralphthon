"""Strict EEVEE shadow-ray configuration, independent of Blender imports.

The caller supplies the real scene. Tests can use a fake scene, but only a real
Blender run can establish runtime RNA support and the recorded readback value.
"""
from __future__ import annotations


def configure_shadow_rays(scene, engine: str, requested: int) -> dict:
    """Apply a supported EEVEE value and report actual readback; fail closed."""
    if type(requested) is not int or not 1 <= requested <= 4:
        raise ValueError("Shadow rays must be an integer from 1 through 4, excluding bool.")
    if engine not in ("eevee", "cycles"):
        raise ValueError("Expected engine 'eevee' or 'cycles'.")
    report = {"requested": requested, "actual": None, "applied": False,
              "property": None, "range": {"cli": [1, 4], "runtime": None}}
    if engine == "cycles":
        if requested != 1:
            raise ValueError("Nondefault EEVEE shadow rays cannot be applied to Cycles.")
        report["note"] = "EEVEE-only setting not applied to Cycles; no EEVEE readback claimed."
        return report

    try:
        eevee = scene.eevee
        initial = eevee.shadow_ray_count
        prop = eevee.bl_rna.properties.get("shadow_ray_count")
        minimum, maximum = prop.hard_min, prop.hard_max
    except (AttributeError, KeyError, TypeError) as exc:
        raise RuntimeError("EEVEE shadow_ray_count and its RNA hard range must be available.") from exc
    if type(initial) is not int:
        raise RuntimeError("EEVEE shadow_ray_count must expose an integer runtime value.")
    if type(minimum) is not int or type(maximum) is not int or minimum > maximum:
        raise RuntimeError("EEVEE shadow_ray_count RNA hard range must contain valid integer bounds.")
    if not minimum <= requested <= maximum:
        raise RuntimeError(f"Requested shadow rays {requested} exceed runtime RNA range {minimum}..{maximum}.")
    try:
        eevee.shadow_ray_count = requested
        actual = eevee.shadow_ray_count
    except Exception as exc:
        raise RuntimeError("EEVEE shadow_ray_count could not be set and read back.") from exc
    if type(actual) is not int or actual != requested:
        raise RuntimeError(f"EEVEE shadow-ray readback mismatch: requested {requested}, actual {actual!r}.")
    report.update({"actual": actual, "applied": True,
                   "property": "scene.eevee.shadow_ray_count",
                   "range": {"cli": [1, 4], "runtime": {"min": minimum, "max": maximum}},
                   "note": "Actual property readback after setting; requested value is never a readback fallback."})
    return report
