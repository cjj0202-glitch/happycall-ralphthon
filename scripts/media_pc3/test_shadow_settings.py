"""Shadow-ray contract/AST checks with fake RNA only; Blender is not executed."""
from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shadow_settings import configure_shadow_rays
from test_look_presets import actual_arguments, function

ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "scripts/media_pc3/build_scene.py"
BASELINE_COMMIT = "8823de2"


class FakeEevee:
    """A setter/readback instrument, not a Blender RNA emulator."""
    def __init__(self, minimum=1, maximum=4, behavior="normal"):
        self.bl_rna = SimpleNamespace(properties={"shadow_ray_count":
            SimpleNamespace(hard_min=minimum, hard_max=maximum)})
        self.behavior, self.writes, self.reads, self._actual = behavior, [], 0, 1
        self.taa_render_samples = 32

    @property
    def shadow_ray_count(self):
        self.reads += 1
        return self._actual

    @shadow_ray_count.setter
    def shadow_ray_count(self, value):
        self.writes.append(value)
        if self.behavior == "raise":
            raise AttributeError("Read-only simulated runtime property")
        self._actual = {"clamp": 2, "ignore": 1, "bool": True,
                        "float": 4.0, "missing": None}.get(self.behavior, value)


class NoEeveeAccess:
    @property
    def eevee(self):
        raise AssertionError("Cycles must not inspect or modify EEVEE")


class ShadowSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = GENERATOR.read_text(encoding="utf-8-sig")
        cls.previous = subprocess.check_output(["git", "show", f"{BASELINE_COMMIT}:scripts/media_pc3/build_scene.py"],
                                               cwd=ROOT, text=True, encoding="utf-8")
        cls.flags = ["--layout", "layout.json", "--output", "output"]

    def test_supported_values_use_actual_property_readback_independent_of_samples(self):
        for requested in (1, 2, 3, 4):
            with self.subTest(requested=requested):
                runtime = FakeEevee()
                scene = SimpleNamespace(eevee=runtime, cycles=SimpleNamespace(samples=64))
                result = configure_shadow_rays(scene, "eevee", requested)
                self.assertEqual(result["requested"], requested)
                self.assertEqual(result["actual"], requested)
                self.assertIs(type(result["actual"]), int)
                self.assertIs(result["applied"], True)
                self.assertEqual(result["property"], "scene.eevee.shadow_ray_count")
                self.assertEqual(result["range"], {"cli": [1, 4], "runtime": {"min": 1, "max": 4}})
                self.assertEqual(runtime.writes, [requested])
                self.assertGreater(runtime.reads, 0)
                self.assertEqual((runtime.taa_render_samples, scene.cycles.samples), (32, 64))

    def test_invalid_requests_and_engine_rejected_without_property_writes(self):
        for requested in (0, 5, 8, -1, True, False, 1.0, 4.0, "4", None, [], {}):
            with self.subTest(requested=requested):
                runtime = FakeEevee()
                with self.assertRaises(ValueError):
                    configure_shadow_rays(SimpleNamespace(eevee=runtime), "eevee", requested)
                self.assertEqual(runtime.writes, [])
        for engine in ("EEVEE", "CYCLES", "unknown", None, False):
            with self.subTest(engine=engine), self.assertRaises(ValueError):
                configure_shadow_rays(NoEeveeAccess(), engine, 1)

    def test_runtime_range_is_recorded_and_checked_before_assignment(self):
        runtime = FakeEevee(maximum=2)
        result = configure_shadow_rays(SimpleNamespace(eevee=runtime), "eevee", 2)
        self.assertEqual(result["range"]["runtime"], {"min": 1, "max": 2})
        runtime = FakeEevee(maximum=2)
        with self.assertRaises(RuntimeError):
            configure_shadow_rays(SimpleNamespace(eevee=runtime), "eevee", 4)
        self.assertEqual(runtime.writes, [])

    def test_missing_runtime_properties_fail_without_synthetic_success(self):
        cases = [SimpleNamespace(), SimpleNamespace(eevee=None),
                 SimpleNamespace(eevee=SimpleNamespace()),
                 SimpleNamespace(eevee=SimpleNamespace(bl_rna=SimpleNamespace())),
                 SimpleNamespace(eevee=SimpleNamespace(bl_rna=SimpleNamespace(properties={}))),
                 SimpleNamespace(eevee=SimpleNamespace(bl_rna=SimpleNamespace(properties={
                     "shadow_ray_count": SimpleNamespace(hard_min=1, hard_max=4)})))]
        for index, scene in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                configure_shadow_rays(scene, "eevee", 1)

    def test_setter_errors_clamps_ignored_writes_and_noninteger_readbacks_fail(self):
        for behavior in ("raise", "clamp", "ignore", "bool", "float", "missing"):
            with self.subTest(behavior=behavior):
                runtime = FakeEevee(behavior=behavior)
                with self.assertRaises(RuntimeError):
                    configure_shadow_rays(SimpleNamespace(eevee=runtime), "eevee", 4)
                self.assertEqual(runtime.writes, [4])

    def test_malformed_runtime_ranges_fail_before_assignment(self):
        for minimum, maximum in ((True, 4), (1, True), (1.0, 4), (1, 4.0), (4, 1), (None, 4), (1, None)):
            with self.subTest(minimum=minimum, maximum=maximum):
                runtime = FakeEevee(minimum, maximum)
                with self.assertRaises(RuntimeError):
                    configure_shadow_rays(SimpleNamespace(eevee=runtime), "eevee", 1)
                self.assertEqual(runtime.writes, [])

    def test_cycles_reports_no_application_or_invented_actual_value(self):
        result = configure_shadow_rays(NoEeveeAccess(), "cycles", 1)
        self.assertEqual(result["requested"], 1)
        self.assertIsNone(result["actual"])
        self.assertIs(result["applied"], False)
        self.assertIsNone(result["property"])
        self.assertEqual(result["range"], {"cli": [1, 4], "runtime": None})
        for requested in (2, 3, 4):
            with self.subTest(requested=requested), self.assertRaises(ValueError):
                configure_shadow_rays(NoEeveeAccess(), "cycles", requested)

    def test_returned_ranges_are_isolated(self):
        first = configure_shadow_rays(SimpleNamespace(eevee=FakeEevee()), "eevee", 1)
        first["range"]["cli"][0] = -1
        first["range"]["runtime"]["max"] = 999
        second = configure_shadow_rays(SimpleNamespace(eevee=FakeEevee()), "eevee", 1)
        self.assertEqual(second["range"], {"cli": [1, 4], "runtime": {"min": 1, "max": 4}})

    def test_actual_cli_defaults_and_invalid_values(self):
        current, previous = actual_arguments(self.source, self.flags), actual_arguments(self.previous, self.flags)
        self.assertEqual(current.shadow_rays, 1)
        self.assertEqual({k: v for k, v in vars(current).items() if k != "shadow_rays"}, vars(previous))
        for value in ("1", "2", "3", "4"):
            args = actual_arguments(self.source, self.flags + ["--shadow-rays", value, "--samples", "16"])
            self.assertEqual((args.shadow_rays, args.samples), (int(value), 16))
        for value in ("0", "5", "8", "-1", "True", "False", "1.0", "nan"):
            with self.subTest(value=value), self.assertRaises(SystemExit) as error:
                actual_arguments(self.source, self.flags + ["--shadow-rays", value])
            self.assertEqual(error.exception.code, 2)
        self.assertEqual(actual_arguments(self.source, self.flags + ["--engine", "cycles"]).shadow_rays, 1)
        for value in ("2", "3", "4"):
            with self.subTest(engine="cycles", value=value), self.assertRaises(SystemExit):
                actual_arguments(self.source, self.flags + ["--engine", "cycles", "--shadow-rays", value])

    def test_actual_main_hook_runs_before_tracks_save_render_and_report_uses_readback(self):
        main = function(ast.parse(self.source), "main")
        hook = next(n for n in main.body if isinstance(n, ast.Assign)
                    and ast.unparse(n) == "shadow_rays = configure_shadow_rays(scene, args.engine, args.shadow_rays)")
        hook_index = main.body.index(hook)
        self.assertEqual(ast.unparse(main.body[hook_index - 1]), "scene, parcel, tracked = build(layout, args)")
        self.assertEqual(ast.unparse(main.body[hook_index + 1]), "tracking = tracks(scene, layout, tracked)")
        runtime = FakeEevee()
        scope = {"configure_shadow_rays": configure_shadow_rays,
                 "scene": SimpleNamespace(eevee=runtime), "args": SimpleNamespace(engine="eevee", shadow_rays=4)}
        exec(compile(ast.Module(body=[hook], type_ignores=[]), "<actual-shadow-hook>", "exec"), scope)
        report = next(n.value for n in main.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "report" for t in n.targets))
        key_index = next(i for i, k in enumerate(report.keys) if k.value == "shadowRays")
        actual = eval(compile(ast.Expression(body=report.values[key_index]), "<actual-shadow-report>", "eval"), scope)
        self.assertIs(actual, scope["shadow_rays"])
        self.assertEqual((actual["requested"], actual["actual"]), (4, 4))
        main.body.remove(hook)
        report.keys.pop(key_index)
        report.values.pop(key_index)
        dependencies = report.values[next(i for i, k in enumerate(report.keys) if k.value == "sourceDependencies")]
        added = [n for n in dependencies.elts if ast.unparse(n) == "digest(Path(__file__).with_name('shadow_settings.py'))"]
        self.assertEqual(len(added), 1)
        dependencies.elts.remove(added[0])
        self.assertEqual(ast.dump(main), ast.dump(function(ast.parse(self.previous), "main")))

    def test_all_preexisting_scene_geometry_and_light_helpers_unchanged(self):
        current, previous = ast.parse(self.source), ast.parse(self.previous)
        for old in previous.body:
            if isinstance(old, ast.FunctionDef) and old.name not in {"arguments", "main"}:
                self.assertEqual(ast.dump(function(current, old.name)), ast.dump(old), old.name)
        self.assertEqual(GENERATOR.read_text(encoding="utf-8-sig"), self.source)


if __name__ == "__main__":
    unittest.main()
