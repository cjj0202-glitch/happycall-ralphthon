"""Pure settings for the N03-M2 representative-frame look comparison.

This module does not import Blender, mutate a scene, or perform I/O.
Each call returns a fresh nested dictionary so one render cannot alter another.
"""
from __future__ import annotations

from copy import deepcopy


_PRESETS = {
    "baseline": {
        "worldStrength": 0.32,
        "lightEnergies": {
            "Large soft loading-side light": 3800,
            "Ceiling key": 3300,
            "Warehouse fill": 2100,
            "Chute rim": 1700,
        },
        "concrete": {
            "color": [0.28, 0.30, 0.31],
            "roughness": 0.36,
            "bumpStrength": 0.16,
            "bumpDistance": 0.008,
        },
        "steel": {
            "color": [0.42, 0.46, 0.49],
            "metallic": 0.78,
            "roughness": 0.29,
        },
    },
    "contrast_material_v1": {
        "worldStrength": 0.12,
        "lightEnergies": {
            "Large soft loading-side light": 1800,
            "Ceiling key": 3300,
            "Warehouse fill": 650,
            "Chute rim": 900,
        },
        "concrete": {
            "color": [0.20, 0.215, 0.225],
            "roughness": 0.43,
            "bumpStrength": 0.06,
            "bumpDistance": 0.002,
        },
        "steel": {
            "color": [0.32, 0.35, 0.38],
            "metallic": 0.88,
            "roughness": 0.24,
        },
    },
}


def settings_for(name: str) -> dict[str, object]:
    """Return the exact named preset; aliases and unknown names are rejected."""
    if not isinstance(name, str) or name not in _PRESETS:
        raise ValueError(
            "Unknown look preset; expected 'baseline' or 'contrast_material_v1'."
        )
    return deepcopy(_PRESETS[name])
