"""Read-only look A/B checks using actual generator AST, without Blender.

The reviewed baseline is the local Git object 03291cca. Material/light calls and
their defaults are recorded, not executed by bpy. Geometry coverage is precisely
audit_guard_supports.source_cuboids' documented subset, not every scene mesh.
Neither 32-sample runtime readback nor rendering is verified by this suite.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import copy
import hashlib
import inspect
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_guard_supports import source_cuboids
from look_presets import settings_for
from scene_contract import load_layout

BASELINE_COMMIT = "03291cca"
GENERATOR = ROOT / "scripts/media_pc3/build_scene.py"


def function(tree, name):
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(matches) != 1:
        raise ValueError(f"Expected one actual {name} function")
    return matches[0]


def normalize(value):
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


def safe_expression(expression, scope):
    allowed = (ast.Expression, ast.Constant, ast.Name, ast.Load, ast.Tuple, ast.List,
               ast.Subscript, ast.IfExp, ast.Compare, ast.Eq, ast.Is, ast.IsNot,
               ast.UnaryOp, ast.UAdd, ast.USub)
    wrapper = ast.Expression(body=expression)
    for node in ast.walk(wrapper):
        if not isinstance(node, allowed):
            raise ValueError(f"Unexpected expression node: {type(node).__name__}")
    return eval(compile(wrapper, "<recorded-generator-expression>", "eval"), {"__builtins__": {}}, scope)


def assignment_value(nodes, target_name):
    matches = [node.value for node in nodes if isinstance(node, ast.Assign)
               and any(ast.unparse(target) == target_name for target in node.targets)]
    if len(matches) != 1:
        raise ValueError(f"Expected one actual assignment to {target_name}")
    return matches[0]


def argument_signature(node):
    positional = node.args.posonlyargs + node.args.args
    defaults = [inspect.Parameter.empty] * (len(positional) - len(node.args.defaults))
    defaults += [ast.literal_eval(item) for item in node.args.defaults]
    return inspect.Signature([inspect.Parameter(item.arg, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                                default=default)
                              for item, default in zip(positional, defaults)])


def record_look(source, look_name="baseline"):
    """Evaluate only the actual look assignment, mats dictionary and area calls."""
    tree = ast.parse(source)
    build, material_fn, area_fn = (function(tree, name) for name in ("build", "material", "area"))
    material_signature, area_signature = argument_signature(material_fn), argument_signature(area_fn)
    bump_strength = assignment_value(ast.walk(material_fn), "bump.inputs['Strength'].default_value")
    bump_distance = assignment_value(ast.walk(material_fn), "bump.inputs['Distance'].default_value")
    lights = []

    def material_recorder(*args, **kwargs):
        bound = material_signature.bind(*args, **kwargs)
        bound.apply_defaults()
        values = bound.arguments
        return normalize({key: values[key] for key in ("name", "color", "metallic", "roughness", "noise")} | {
            "bumpStrength": safe_expression(bump_strength, values) if values["noise"] else None,
            "bumpDistance": safe_expression(bump_distance, values) if values["noise"] else None,
        })

    def area_recorder(*args, **kwargs):
        bound = area_signature.bind(*args, **kwargs)
        bound.apply_defaults()
        lights.append(normalize(dict(bound.arguments)))

    selected = []
    for node in build.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in ("look", "mats")
                                                for target in node.targets):
            selected.append(node)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "area":
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    allowed = (ast.Module, ast.Assign, ast.Name, ast.Load, ast.Store, ast.Expr, ast.Call,
               ast.keyword, ast.Dict, ast.List, ast.Tuple, ast.Constant, ast.Subscript,
               ast.Attribute, ast.UnaryOp, ast.UAdd, ast.USub)
    for node in ast.walk(module):
        if not isinstance(node, allowed):
            raise ValueError(f"Unexpected look AST node: {type(node).__name__}")
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id not in {"material", "area", "settings_for"}):
            raise ValueError("Only material/area recorders and settings_for are permitted")
        if isinstance(node, ast.Attribute) and not (isinstance(node.value, ast.Name) and node.value.id == "args" and node.attr == "look"):
            raise ValueError("Only args.look attribute access is permitted")
    scope = {"__builtins__": {}, "args": SimpleNamespace(look=look_name), "settings_for": settings_for,
             "material": material_recorder, "area": area_recorder}
    exec(compile(module, "<recorded-generator-look>", "exec"), scope)
    background = "scene.world.node_tree.nodes['Background'].inputs"
    return {"materials": scope["mats"], "lights": lights,
            "worldStrength": safe_expression(assignment_value(build.body, background + "['Strength'].default_value"), scope),
            "worldColor": normalize(safe_expression(assignment_value(build.body, background + "['Color'].default_value"), scope))}


def actual_arguments(source, flags):
    """Compile the real parser function; no top-level generator imports execute."""
    tree = ast.parse(source)
    scope = {"argparse": argparse, "Path": Path, "__doc__": ast.get_docstring(tree),
             "sys": SimpleNamespace(argv=["blender", "--background", "--"] + list(flags))}
    module = ast.Module(body=[function(tree, "arguments")], type_ignores=[])
    exec(compile(module, "<actual-generator-cli>", "exec"), scope)
    with contextlib.redirect_stderr(io.StringIO()):
        return scope["arguments"]()


class LookPresetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = GENERATOR.read_text(encoding="utf-8-sig")
        cls.baseline_source = subprocess.check_output(
            ["git", "show", f"{BASELINE_COMMIT}:scripts/media_pc3/build_scene.py"],
            cwd=ROOT, text=True, encoding="utf-8")
        cls.flags = ["--layout", "layout.json", "--output", "review-output"]

    def test_returned_settings_are_independent_nested_snapshots(self):
        originals = {name: settings_for(name) for name in ("baseline", "contrast_material_v1")}
        for name in originals:
            with self.subTest(name=name):
                modified = settings_for(name)
                modified["worldStrength"] = -1
                modified["concrete"]["color"][0] = -1
                modified["steel"]["roughness"] = -1
                modified["lightEnergies"]["Ceiling key"] = -1
                self.assertEqual(settings_for(name), originals[name])
        self.assertEqual(settings_for("baseline"), originals["baseline"])
        self.assertEqual(settings_for("contrast_material_v1"), originals["contrast_material_v1"])

    def test_unregistered_preset_names_and_types_rejected(self):
        for name in (None, False, 0, [], {}, "", "BASELINE", "contrast-material-v1"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                settings_for(name)

    def test_actual_cli_defaults_preserve_previous_options_and_select_baseline(self):
        current = actual_arguments(self.source, self.flags)
        previous = actual_arguments(self.baseline_source, self.flags)
        self.assertEqual(current.look, "baseline")
        self.assertEqual({key: value for key, value in vars(current).items() if key != "look"}, vars(previous))
        self.assertEqual((current.mode, current.engine, current.camera, current.samples),
                         ("representatives", "eevee", "cctv", 32))
        self.assertEqual(current.resolution, [1280, 720])

    def test_actual_cli_baseline_modes_and_candidate_representative_limit(self):
        for mode in ("prepare", "representatives", "short", "animation"):
            with self.subTest(look="baseline", mode=mode):
                args = actual_arguments(self.source, self.flags + ["--mode", mode, "--look", "baseline"])
                self.assertEqual((args.mode, args.look), (mode, "baseline"))
            with self.subTest(look="contrast_material_v1", mode=mode):
                flags = self.flags + ["--mode", mode, "--look", "contrast_material_v1"]
                if mode in ("prepare", "representatives"):
                    self.assertEqual(actual_arguments(self.source, flags).look, "contrast_material_v1")
                else:
                    with self.assertRaises(SystemExit) as failure:
                        actual_arguments(self.source, flags)
                    self.assertEqual(failure.exception.code, 2)

    def test_actual_cli_rejects_unregistered_look_and_preserves_camera_gate(self):
        for flags in (["--look", "unknown"], ["--look", "BASELINE"], ["--look", "contrast-material-v1"],
                      ["--mode", "animation", "--camera", "overview"]):
            with self.subTest(flags=flags), self.assertRaises(SystemExit) as failure:
                actual_arguments(self.source, self.flags + flags)
            self.assertEqual(failure.exception.code, 2)

    def test_actual_baseline_material_light_and_world_calls_match_reviewed_commit(self):
        current, previous = record_look(self.source), record_look(self.baseline_source)
        self.assertEqual(current, previous)
        self.assertEqual(len(current["materials"]), 11)
        self.assertEqual(len(current["lights"]), 4)
        self.assertEqual(current["materials"]["floor"]["bumpStrength"], 0.16)
        self.assertEqual(current["materials"]["floor"]["bumpDistance"], 0.008)
        for name in ("belt", "card"):
            self.assertEqual(current["materials"][name]["bumpStrength"], 0.16)
            self.assertEqual(current["materials"][name]["bumpDistance"], 0.001)

    def test_candidate_changes_only_supported_material_world_and_energy_fields(self):
        baseline, candidate = record_look(self.source), record_look(self.source, "contrast_material_v1")
        allowed = {"floor": {"color", "roughness", "bumpStrength", "bumpDistance"},
                   "steel": {"color", "metallic", "roughness"}}
        self.assertEqual(set(candidate["materials"]), set(baseline["materials"]))
        for name, previous in baseline["materials"].items():
            changed = {key for key in previous if previous[key] != candidate["materials"][name][key]}
            self.assertEqual(changed, allowed.get(name, set()), name)
        self.assertEqual(candidate["materials"]["floor"]["bumpStrength"], 0.06)
        self.assertEqual(candidate["materials"]["floor"]["bumpDistance"], 0.002)
        self.assertEqual(candidate["worldColor"], baseline["worldColor"])
        self.assertEqual((baseline["worldStrength"], candidate["worldStrength"]), (0.32, 0.12))
        changed_lights = []
        for old, new in zip(baseline["lights"], candidate["lights"]):
            self.assertEqual({k: v for k, v in old.items() if k != "energy"},
                             {k: v for k, v in new.items() if k != "energy"})
            if old["energy"] != new["energy"]:
                changed_lights.append(old["name"])
        self.assertEqual(changed_lights, ["Large soft loading-side light", "Warehouse fill", "Chute rim"])
        self.assertEqual([item["energy"] for item in candidate["lights"]], [1800, 3300, 650, 900])

    def test_explicit_color_management_configuration_is_fixed(self):
        build = function(ast.parse(self.source), "build")
        assignment = next(node for node in build.body if isinstance(node, ast.Assign)
                          and any(ast.unparse(target) == "(scene.view_settings.exposure, scene.view_settings.gamma)"
                                  for target in node.targets))
        self.assertEqual(safe_expression(assignment.value, {}), (0, 1))
        self.assertEqual(safe_expression(assignment_value(build.body, "scene.view_settings.view_transform"), {}), "AgX")

    def test_audited_source_cuboids_match_reviewed_geometry(self):
        planning = ROOT / "planning/media/scene-layout-v1.json"
        layout_path = planning if planning.exists() else ROOT / ".local/pc3-blender/input/scene-layout-v1.json"
        layout = load_layout(layout_path, ROOT / "data/fixtures/cases.json")
        old = source_cuboids(self.baseline_source, layout)
        current = source_cuboids(self.source, layout)
        self.assertTrue(current)
        self.assertEqual(current, old)
        self.assertEqual(sum(item["name"].endswith("guard support") for item in current), 18)
        self.assertEqual(sum(item["parented"] for item in current), 3)

    def test_recorders_detect_changed_material_light_and_guard_inputs(self):
        baseline = record_look(self.source)
        tree = ast.parse(self.source)
        build = function(tree, "build")
        mats = next(node.value for node in build.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "mats" for target in node.targets))
        concrete = next(value for key, value in zip(mats.keys, mats.values) if key.value == "floor")
        roughness = next(keyword for keyword in concrete.keywords if keyword.arg == "roughness")
        roughness.value = ast.Constant(value=0.99)
        self.assertNotEqual(record_look(ast.unparse(ast.fix_missing_locations(tree))), baseline)
        tree = ast.parse(self.source)
        build = function(tree, "build")
        light = next(node.value for node in build.body if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                     and isinstance(node.value.func, ast.Name) and node.value.func.id == "area")
        light.args[3] = ast.Constant(value=9999)
        self.assertNotEqual(record_look(ast.unparse(ast.fix_missing_locations(tree))), baseline)
        planning = ROOT / "planning/media/scene-layout-v1.json"
        layout = load_layout(planning if planning.exists() else ROOT / ".local/pc3-blender/input/scene-layout-v1.json")
        tree = ast.parse(self.source)
        guard = next(node for node in ast.walk(function(tree, "build")) if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Name) and node.func.id == "cube" and node.args
                     and isinstance(node.args[0], ast.Constant) and node.args[0].value == "North guard support")
        guard.args[2].elts[0] = ast.Constant(value=0.07)
        self.assertNotEqual(source_cuboids(ast.unparse(ast.fix_missing_locations(tree)), layout),
                            source_cuboids(self.source, layout))

    def test_generator_source_unchanged_during_review(self):
        self.assertEqual(GENERATOR.read_text(encoding="utf-8-sig"), self.source)


if __name__ == "__main__":
    unittest.main()
