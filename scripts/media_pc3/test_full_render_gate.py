"""N03-M4 artificial receipts and actual-main boundary tests; never runs Blender.

All receipts live in isolated .local test directories and are labelled artificial.
They are not approvals issued by pc1. The render stub stops at its first call.
"""
from __future__ import annotations

import ast
import argparse
import contextlib
import copy
from functools import lru_cache
import hashlib
import importlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SCRATCH = ROOT / ".local/pc3-full-render-gate"
GENERATOR = HERE / "build_scene.py"
GATE = HERE / "full_render_gate.py"
sys.path.insert(0, str(HERE))
from test_render_package import make_package, png

DEPENDENCIES = ("scene_contract.py", "look_presets.py", "environment_detail.py", "shadow_settings.py", "full_render_gate.py")
SETTINGS = {"camera": "cctv", "resolution": [1920, 1080], "engine": "eevee", "samples": 96,
            "shadowRays": 4, "look": "contrast_material_v1", "environmentDetail": "staging_v1",
            "threads": 2, "fps": 24, "frames": 288}
NEGATIVES = set()
MUTANTS = []


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def descriptor(path, base):
    path = Path(path)
    data = path.read_bytes()
    return {"path": path.relative_to(base).as_posix(), "bytes": len(data), "sha256": sha(data)}


@lru_cache(maxsize=1)
def artificial_short_report():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="artificial-short-seed-", dir=SCRATCH) as directory:
        package, _ = make_package(Path(directory), "short")
        return (package / "render-report.json").read_bytes()


def make_receipt(base):
    """Create the one approved-shape ARTIFICIAL fixture, never a production receipt."""
    base = Path(base)
    current, inputs, evidence = base / "current", base / "input", base / "ARTIFICIAL-evidence"
    for directory in (current, inputs, evidence):
        directory.mkdir(parents=True)
    for name in ("build_scene.py", *DEPENDENCIES):
        (current / name).write_bytes((HERE / name).read_bytes())
    layout = inputs / "scene-layout-v1.json"
    layout.write_bytes((ROOT / "reports/pc3/render-package-test-layout.json").read_bytes())
    fixture = inputs / "cases.json"
    write_json(fixture, {"notice": "ARTIFICIAL TEST INPUT, not operational or reviewed by pc1", "cases": []})
    representatives = []
    image = png(1920, 1080)
    for frame in (1, 133, 288):
        path = evidence / f"frame-{frame:04d}.png"
        path.write_bytes(image)
        representatives.append({"role": "reviewed-representative", "frame": frame,
                                "resolution": [1920, 1080], **descriptor(path, base)})
    (evidence / "ARTIFICIAL-short").mkdir()
    short = evidence / "ARTIFICIAL-short/render-report.json"
    short.write_bytes(artificial_short_report())
    receipt = {"schemaVersion": "pc3-animation-review-v1", "reviewId": "ARTIFICIAL-TEST-NOT-PC1-APPROVAL",
               "scope": "synthetic-full-animation-candidate", "settings": copy.deepcopy(SETTINGS),
               "sources": {"generator": descriptor(current / "build_scene.py", base),
                           "dependencies": [descriptor(current / name, base) for name in DEPENDENCIES],
                           "layout": descriptor(layout, base), "fixture": descriptor(fixture, base)},
               "evidence": {"representatives": representatives,
                            "shortReport": {"role": "reviewed-short-report", "resolution": [1280, 720],
                                            "frameStart": 73, "frameEnd": 144, "renderedFrameCount": 72,
                                            **descriptor(short, base)}}}
    path = base / "ARTIFICIAL-TEST-NOT-APPROVED-receipt.json"
    write_json(path, receipt)
    args = SimpleNamespace(mode="animation", camera="cctv", resolution=[1920, 1080], engine="eevee",
                           samples=96, shadow_rays=4, threads=2, look="contrast_material_v1", environment_detail="staging_v1",
                           layout=layout, fixture=fixture, output=base / "not-created-unless-preflight-passes",
                           animation_review=path, animation_review_sha256=sha(path.read_bytes()))
    return args, current / "build_scene.py", receipt


def expected_readback():
    direction = [-7, 6, -7.15]
    length = math.sqrt(sum(v*v for v in direction))
    forward = [v/length for v in direction]
    up = [(1 if i == 2 else 0) - forward[2]*forward[i] for i in range(3)]
    up_length = math.sqrt(sum(v*v for v in up))
    return {"engine": "BLENDER_EEVEE_NEXT", "samples": 96, "shadowRays": 4, "threadsMode": "FIXED", "threads": 2,
            "resolution": [1920, 1080], "resolutionPercentage": 100, "pixelAspect": [1, 1],
            "fps": 24, "fpsBase": 1, "frameStart": 1, "frameEnd": 288,
            "camera": {"name": "SYN-CAM-02", "type": "PERSP", "shift": [0, 0], "position": [24, 1, 8],
                       "forward": forward, "up": [v/up_length for v in up],
                       "lens": 32, "sensorWidth": 36, "sensorFit": "HORIZONTAL"}}


class MockRenderReached(Exception):
    """Raised by the stub at the first render invocation; no image is rendered."""


class StubVector(list):
    def __neg__(self):
        return StubVector(-v for v in self)

    def normalize(self):
        length = math.sqrt(sum(v*v for v in self))
        self[:] = [v/length for v in self]


def main_harness(generator_source, generator_path, args, gate, layout, readback=None, after_tracks=None):
    """Compile actual arguments/collector/main only; stub bpy and renderer dependencies."""
    observed = copy.deepcopy(readback or expected_readback())
    calls = {"build": 0, "tracks": 0, "save": 0, "render": 0, "updates": 0, "frames": []}
    class CameraMatrix:
        translation = StubVector(observed["camera"]["position"])
        def to_3x3(self):
            return self
        def __matmul__(self, vector):
            if list(vector) == [0, 0, 1]:
                return StubVector(-v for v in observed["camera"]["forward"])
            if list(vector) == [0, 1, 0]:
                return StubVector(observed["camera"]["up"])
            raise AssertionError("Unexpected actual collector matrix operation")
    camera_data = SimpleNamespace(type=observed["camera"]["type"], shift_x=observed["camera"]["shift"][0],
                                  shift_y=observed["camera"]["shift"][1], lens=observed["camera"]["lens"],
                                  sensor_width=observed["camera"]["sensorWidth"], sensor_fit=observed["camera"]["sensorFit"])
    scene = SimpleNamespace(render=SimpleNamespace(engine=observed["engine"], threads_mode=observed["threadsMode"],
        threads=observed["threads"], resolution_x=observed["resolution"][0], resolution_y=observed["resolution"][1],
        resolution_percentage=observed["resolutionPercentage"], pixel_aspect_x=observed["pixelAspect"][0],
        pixel_aspect_y=observed["pixelAspect"][1], fps=observed["fps"], fps_base=observed["fpsBase"]),
        eevee=SimpleNamespace(taa_render_samples=observed["samples"], shadow_ray_count=observed["shadowRays"]),
        cycles=SimpleNamespace(samples=16), frame_start=observed["frameStart"], frame_end=observed["frameEnd"],
        camera=SimpleNamespace(name=observed["camera"]["name"], data=camera_data, matrix_world=CameraMatrix()),
        frame_set=lambda frame:calls["frames"].append(frame))
    def build(_layout, _args):
        calls["build"] += 1
        return scene, object(), []
    def tracks(_scene, _layout, _tracked):
        calls["tracks"] += 1
        if after_tracks:
            after_tracks()
        return {"clippedFrames": [], "notice": "ARTIFICIAL MAIN STUB, not renderer tracks"}
    def save_as_mainfile(filepath):
        calls["save"] += 1
        Path(filepath).write_bytes(b"ARTIFICIAL STUB NOT A BLENDER FILE")
    def render(**_kwargs):
        calls["render"] += 1
        raise MockRenderReached("First renderer stub reached; no rendering performed")
    def update():
        calls["updates"] += 1
    cli = ["blender", "--", "--layout", str(args.layout), "--fixture", str(args.fixture), "--output", str(args.output),
           "--mode", args.mode, "--engine", args.engine, "--camera", args.camera,
           "--resolution", *map(str, args.resolution), "--samples", str(args.samples),
           "--shadow-rays", str(args.shadow_rays), "--look", args.look, "--environment-detail", args.environment_detail]
    if args.threads is not None:
        cli += ["--threads", str(args.threads)]
    if args.animation_review is not None:
        cli += ["--animation-review", str(args.animation_review)]
    if args.animation_review_sha256 is not None:
        cli += ["--animation-review-sha256", args.animation_review_sha256]
    scope = {"argparse": argparse, "Path": Path, "sys": SimpleNamespace(argv=cli), "__doc__": "Actual main stub test",
             "__file__": str(generator_path), "json": json, "time": time, "FRAME_COUNT": 288,
             "Vector": StubVector, "verify_animation_review": gate.verify_animation_review,
             "validate_scene_readback": gate.validate_scene_readback,
             "load_layout": lambda *_args, **_kwargs: copy.deepcopy(layout), "build": build, "tracks": tracks,
             "configure_shadow_rays": lambda s,e,r: {"requested": r, "actual": s.eevee.shadow_ray_count, "applied": True},
             "bpy": SimpleNamespace(context=SimpleNamespace(view_layer=SimpleNamespace(update=update)),
                                    ops=SimpleNamespace(wm=SimpleNamespace(save_as_mainfile=save_as_mainfile),
                                                        render=SimpleNamespace(render=render)))}
    tree = ast.parse(generator_source)
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name in {"arguments", "scene_readback", "main"}]
    if {node.name for node in selected} != {"arguments", "scene_readback", "main"}:
        raise ValueError("Expected actual parser, collector and main functions")
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<actual-generator-main>", "exec"), scope)
    return scope["main"], calls, scene


class FullRenderGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = importlib.import_module("full_render_gate")
        SCRATCH.mkdir(parents=True, exist_ok=True)
        cls.source_bytes = {}
        for name, path in (("gate", GATE), ("generator", GENERATOR)):
            data = path.read_bytes()
            backup = SCRATCH / f"original-{name}-{sha(data)}.py"
            if not backup.exists():
                backup.write_bytes(data)
            if backup.read_bytes() != data:
                raise RuntimeError("Original source backup differs")
            cls.source_bytes[name] = data

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="ARTIFICIAL-", dir=SCRATCH)
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.args, self.generator, self.receipt = make_receipt(self.base)
        self.receipt_original = self.args.animation_review.read_bytes()
        self.layout = json.loads(self.args.layout.read_text(encoding="utf-8-sig"))

    def refresh_receipt(self, change=None):
        value = copy.deepcopy(self.receipt)
        if change:
            change(value)
        write_json(self.args.animation_review, value)
        self.args.animation_review_sha256 = sha(self.args.animation_review.read_bytes())
        return value

    def verify(self):
        return self.gate.verify_animation_review(self.args, self.generator)

    def rejected(self, name, message=None):
        before = {p.relative_to(self.base).as_posix(): sha(p.read_bytes()) for p in self.base.rglob("*")
                  if p.is_file() and not p.is_symlink()}
        with self.assertRaises(self.gate.GateError) as caught:
            self.verify()
        if message:
            self.assertIn(message, str(caught.exception))
        after = {p.relative_to(self.base).as_posix(): sha(p.read_bytes()) for p in self.base.rglob("*")
                 if p.is_file() and not p.is_symlink()}
        self.assertEqual(before, after)
        self.assertFalse(self.args.output.exists())
        NEGATIVES.add(name)

    def test_complete_artificial_receipt_allowed_without_claiming_authentication(self):
        result = self.verify()
        self.assertEqual(result["schemaVersion"], "pc3-animation-review-verification-v1")
        self.assertEqual(result["settings"], SETTINGS)
        self.assertIs(result["issuerAuthenticated"], False)
        self.assertIs(result["visualAccepted"], False)
        self.assertEqual(result["receipt"]["sha256"], self.args.animation_review_sha256)
        self.assertFalse(self.args.output.exists())

    def test_missing_receipt_pair_and_wrong_expected_sha_rejected(self):
        for name, path, expected_sha in (("missing-both", None, None),
                                         ("missing-file", self.base / "absent.json", "0"*64),
                                         ("missing-sha", self.args.animation_review, None),
                                         ("missing-path", None, self.args.animation_review_sha256),
                                         ("wrong-expected-sha", self.args.animation_review, "0"*64)):
            with self.subTest(name=name):
                args = copy.copy(self.args)
                args.animation_review, args.animation_review_sha256 = path, expected_sha
                with self.assertRaises(self.gate.GateError):
                    self.gate.verify_animation_review(args, self.generator)
                self.assertFalse(args.output.exists())
                NEGATIVES.add(name)

    def test_execution_settings_drift_is_rejected(self):
        for field, value in (("camera", "overview"), ("resolution", [1280, 720]), ("engine", "cycles"),
                             ("samples", 32), ("shadow_rays", 1), ("threads", None), ("threads", 4), ("look", "baseline"),
                             ("environment_detail", "none"), ("samples", True), ("resolution", [1920, "1080"])):
            with self.subTest(field=field, value=value):
                args = copy.copy(self.args)
                setattr(args, field, value)
                with self.assertRaises(self.gate.GateError):
                    self.gate.verify_animation_review(args, self.generator)
                NEGATIVES.add(f"args-{field}-{value}")

    def test_receipt_schema_required_roles_duplicates_and_settings_are_strict(self):
        variants = [("schema", lambda r: r.update(schemaVersion="unknown")),
                    ("approved-only", lambda r: (r.clear(), r.update(approved=True))),
                    ("scope", lambda r: r.update(scope="final-product-accepted")),
                    ("missing-fixture", lambda r: r["sources"].pop("fixture")),
                    ("missing-dependency", lambda r: r["sources"]["dependencies"].pop()),
                    ("duplicate-dependency", lambda r: r["sources"]["dependencies"].__setitem__(1,r["sources"]["dependencies"][0])),
                    ("missing-representative", lambda r: r["evidence"]["representatives"].pop()),
                    ("duplicate-representative", lambda r: r["evidence"]["representatives"].__setitem__(1,r["evidence"]["representatives"][0])),
                    ("wrong-evidence-role", lambda r: r["evidence"]["shortReport"].update(role="unreviewed")),
                    ("wrong-evidence-count", lambda r: r["evidence"]["shortReport"].update(renderedFrameCount=288)),
                    ("wrong-evidence-resolution", lambda r: r["evidence"]["representatives"][0].update(resolution=[1280,720])),
                    ("boolean-frame", lambda r: r["evidence"]["representatives"][0].update(frame=True)),
                    ("wrong-thread-count", lambda r: r["settings"].update(threads=4)),
                    ("wrong-shadow-unit", lambda r: r["settings"].update(shadowRays="4")),
                    ("wrong-camera", lambda r: r["settings"].update(camera="overview")),
                    ("traversal", lambda r: r["sources"]["generator"].update(path="../outside.py")),
                    ("absolute-path", lambda r: r["sources"]["layout"].update(path=str(self.args.layout))),
                    ("windows-separator", lambda r: r["sources"]["layout"].update(path="input\\scene-layout-v1.json")),
                    ("duplicate-source-evidence-path", lambda r: r["evidence"]["representatives"][1].update(path=r["evidence"]["representatives"][0]["path"])),
                    ("boolean-byte-count", lambda r: r["sources"]["fixture"].update(bytes=True))]
        for name, change in variants:
            with self.subTest(name=name):
                self.refresh_receipt(change)
                self.rejected("receipt-"+name)

    def test_changed_or_missing_source_input_and_evidence_file_is_rejected(self):
        targets = [self.generator, self.args.layout, self.args.fixture,
                   self.base / self.receipt["sources"]["dependencies"][-1]["path"],
                   self.base / self.receipt["evidence"]["representatives"][1]["path"],
                   self.base / self.receipt["evidence"]["shortReport"]["path"]]
        for target in targets:
            original = target.read_bytes()
            try:
                with self.subTest(changed=target.name):
                    target.write_bytes(original+b"TAMPERED")
                    self.rejected("changed-file-"+target.name)
                with self.subTest(missing=target.name):
                    target.unlink()
                    self.rejected("missing-file-"+target.name)
            finally:
                target.write_bytes(original)
        replacement = self.base / "unreviewed-layout.json"
        replacement.write_bytes(self.args.layout.read_bytes())
        self.args.layout = replacement
        self.rejected("different-input-basename-even-identical-bytes")

    def test_corrupted_representative_and_wrong_short_report_rejected_with_updated_hash(self):
        path = self.base / self.receipt["evidence"]["representatives"][0]["path"]
        path.write_bytes(png(1280, 720))
        self.refresh_receipt(lambda r: r["evidence"]["representatives"][0].update(descriptor(path,self.base)))
        self.rejected("wrong-png-dimensions-correct-hash")
        path.write_bytes(png(1920,1080)[:-12])
        self.refresh_receipt(lambda r: r["evidence"]["representatives"][0].update(descriptor(path,self.base)))
        self.rejected("truncated-png-correct-hash")
        path.write_bytes(png(1920,1080))
        short = self.base / self.receipt["evidence"]["shortReport"]["path"]
        value=json.loads(short.read_text(encoding="utf-8"))
        value["cameraId"]="OTHER"
        write_json(short,value)
        self.refresh_receipt(lambda r:r["evidence"]["shortReport"].update(descriptor(short,self.base)))
        self.rejected("wrong-short-camera-correct-hash")

    def test_readback_actual_values_and_every_required_runtime_dimension(self):
        readback = expected_readback()
        self.gate.validate_scene_readback(readback, self.layout)
        variants = [(key,value) for key,value in
                    (("engine","CYCLES"),("samples",32),("samples",True),("shadowRays",1),
                     ("threadsMode","AUTO"),("threads",4),("resolution",[1280,720]),
                     ("resolutionPercentage",50),("pixelAspect",[1,2]),("fps",30),("fpsBase",1.001),
                     ("frameStart",0),("frameEnd",72))]
        for key,value in variants:
            with self.subTest(key=key,value=value):
                changed=copy.deepcopy(readback);changed[key]=value
                with self.assertRaises(self.gate.GateError):self.gate.validate_scene_readback(changed,self.layout)
                NEGATIVES.add(f"readback-{key}-{value}")
        for key,value in (("name","SYN-OVERVIEW-NOT-CCTV"),("position",[25,1,8]),("forward",[0,0,-1]),
                          ("up",[0,0,1]),("type","ORTHO"),("shift",[.1,0]),
                          ("lens",36),("sensorWidth",35),("sensorFit","VERTICAL")):
            with self.subTest(camera=key):
                changed=copy.deepcopy(readback);changed["camera"][key]=value
                with self.assertRaises(self.gate.GateError):self.gate.validate_scene_readback(changed,self.layout)
                NEGATIVES.add("readback-camera-"+key)

    def test_hardlink_and_junction_evidence_rejected(self):
        path=self.base/self.receipt["evidence"]["representatives"][0]["path"]
        outside=self.base/"outside-original.png"
        original=path.read_bytes();outside.write_bytes(original);path.unlink()
        try:
            os.link(outside,path)
            self.rejected("hardlink-evidence", "without hard links")
            self.assertEqual(outside.read_bytes(),original)
        finally:
            path.unlink();path.write_bytes(original)
        target=self.base/"junction-target";target.mkdir()
        (target/"frame-0001.png").write_bytes(original)
        linked=self.base/"junction-evidence"
        if os.name=="nt":
            created=subprocess.run(["cmd","/c","mklink","/J",str(linked),str(target)],capture_output=True,text=True)
            if created.returncode:self.skipTest("OS refused isolated test junction")
        else:linked.symlink_to(target,target_is_directory=True)
        try:
            self.refresh_receipt(lambda r:r["evidence"]["representatives"][0].update(path="junction-evidence/frame-0001.png"))
            self.rejected("junction-evidence", "Links and reparse points")
        finally:
            self.assertEqual(linked.parent.resolve(),self.base.resolve())
            if linked.is_symlink():linked.unlink()
            elif linked.is_junction():linked.rmdir()

    def test_symlink_evidence_rejected_if_os_allows_creation(self):
        path=self.base/self.receipt["evidence"]["representatives"][0]["path"]
        outside=self.base/"outside-symlink-original.png"
        original=path.read_bytes();outside.write_bytes(original);path.unlink()
        try:
            try:path.symlink_to(outside)
            except OSError as error:self.skipTest(f"OS denied symlink creation; no privilege change: {error}")
            self.rejected("symlink-evidence")
        finally:
            if path.is_symlink():path.unlink()

    def main_runner(self, **options):
        return main_harness(self.source_bytes["generator"], self.generator, self.args,
                            self.gate, self.layout, **options)

    def test_actual_main_artificial_positive_reaches_first_stub_render(self):
        main, calls, _ = self.main_runner()
        with self.assertRaises(MockRenderReached):
            main()
        self.assertEqual({key:calls[key] for key in ("build", "tracks", "save", "render")},
                         {"build":1, "tracks":1, "save":1, "render":1})
        self.assertEqual(calls["updates"], 2)
        self.assertEqual(calls["frames"], [1, 1])
        self.assertFalse(any(self.args.output.glob("frame-*.png")))

    def test_actual_main_wrong_receipt_sha_rejects_before_mkdir(self):
        self.args.animation_review_sha256 = "0"*64
        main, calls, _ = self.main_runner()
        try:
            main()
        except self.gate.GateError:
            pass
        except MockRenderReached:
            self.fail("Wrong expected receipt SHA reached the renderer")
        else:
            self.fail("Wrong expected receipt SHA was accepted")
        self.assertFalse(self.args.output.exists())
        self.assertEqual([calls[key] for key in ("build", "tracks", "save", "render")], [0,0,0,0])
        NEGATIVES.add("actual-main-wrong-sha-before-mkdir")

    def test_actual_main_parser_missing_receipt_and_overview_reject_before_mkdir(self):
        original = copy.copy(self.args)
        for name, changes in (("missing-receipt", {"animation_review":None,"animation_review_sha256":None}),
                              ("missing-sha", {"animation_review_sha256":None}),
                              ("overview-with-receipt", {"camera":"overview"})):
            with self.subTest(name=name):
                self.args = copy.copy(original)
                self.args.__dict__.update(changes)
                main, calls, _ = self.main_runner()
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    main()
                self.assertFalse(self.args.output.exists())
                self.assertEqual([calls[key] for key in ("build", "tracks", "save", "render")], [0,0,0,0])
                NEGATIVES.add("actual-main-parser-"+name)

    def test_actual_main_bad_runtime_readback_rejects_before_tracks_or_render(self):
        readback = expected_readback()
        readback["samples"] = 32
        main, calls, _ = self.main_runner(readback=readback)
        with self.assertRaises(self.gate.GateError):
            main()
        self.assertEqual([calls[key] for key in ("build", "tracks", "save", "render")], [1,0,0,0])
        self.assertEqual(list(self.args.output.iterdir()), [])
        NEGATIVES.add("actual-main-runtime32-request96-before-tracks")

    def test_actual_main_second_verification_detects_changed_input_before_render(self):
        def change_input():
            self.args.fixture.write_bytes(self.args.fixture.read_bytes()+b"\nTAMPERED AFTER TRACKING")
        main, calls, _ = self.main_runner(after_tracks=change_input)
        with self.assertRaises(self.gate.GateError):
            main()
        self.assertEqual([calls[key] for key in ("build", "tracks", "save", "render")], [1,1,1,0])
        self.assertFalse(any(self.args.output.glob("frame-*.png")))
        NEGATIVES.add("actual-main-input-change-before-first-render")

    def test_actual_main_second_readback_detects_changed_scene_before_render(self):
        main, calls, scene = self.main_runner(after_tracks=lambda:setattr(scene.eevee, "taa_render_samples", 32))
        with self.assertRaises(self.gate.GateError):
            main()
        self.assertEqual([calls[key] for key in ("build", "tracks", "save", "render")], [1,1,1,0])
        self.assertEqual(calls["updates"], 2)
        self.assertFalse(any(self.args.output.glob("frame-*.png")))
        NEGATIVES.add("actual-main-readback-change-before-first-render")

    def test_disabled_receipt_sha_guard_is_killed_by_actual_main_negative(self):
        tree = ast.parse(self.source_bytes["gate"])
        changed = 0
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "require"
                    and len(node.args) > 1 and isinstance(node.args[1], ast.Constant)
                    and node.args[1].value == "Animation review receipt SHA256 differs from the supplied expectation."):
                node.args[0] = ast.Constant(True)
                changed += 1
        self.assertEqual(changed, 1, "Mutation must target exactly the independent receipt SHA guard")
        namespace = {"__file__":str(GATE), "__name__":"_artificial_gate_mutant"}
        exec(compile(ast.fix_missing_locations(tree), "<in-memory-disabled-sha-gate>", "exec"), namespace)
        suite = unittest.TestSuite([FullRenderGateTests("test_actual_main_wrong_receipt_sha_rejects_before_mkdir")])
        result = unittest.TestResult()
        with mock.patch.object(self.gate, "verify_animation_review", namespace["verify_animation_review"]):
            suite.run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 1)
        self.assertIn("Wrong expected receipt SHA reached the renderer", result.failures[0][1])
        self.assertEqual(GATE.read_bytes(), self.source_bytes["gate"])
        self.assertEqual(GENERATOR.read_bytes(), self.source_bytes["generator"])
        MUTANTS.append({"mutation":"receipt SHA guard disabled in memory", "testsRun":1,
                        "killed":True, "failures":1, "errors":0, "sourceFilesChanged":False})

    def test_original_gate_and_generator_sources_remain_unchanged(self):
        self.assertEqual(GATE.read_bytes(),self.source_bytes["gate"])
        self.assertEqual(GENERATOR.read_bytes(),self.source_bytes["generator"])


if __name__ == "__main__":
    unittest.main()
