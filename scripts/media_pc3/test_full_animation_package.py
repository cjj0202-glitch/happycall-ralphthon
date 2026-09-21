"""Independent N03-M5 full-output tests; flat PNGs are NOT Blender renders.

Expectations are constructed before the report from separate source/input bytes
and fixed settings. No test receipt is approval from pc1, and no pixels or video
are decoded. Existing generator/gate/checker sources remain read-only.
"""
from __future__ import annotations

import ast
import copy
from functools import lru_cache
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SCRATCH = ROOT / ".local/pc3-m5-intake"
CHECKER = HERE / "verify_full_animation.py"
sys.path.insert(0, str(HERE))
from test_render_package import make_package, digest, png, write_json, mutate_report, mutate_tracks, update_asset_digest
from test_full_render_gate import make_receipt, expected_readback, SETTINGS, DEPENDENCIES
from full_render_gate import verify_animation_review

NEGATIVE_CASES = set()
MUTATIONS = []


@lru_cache(maxsize=1)
def artificial_seed():
    """Use existing independent geometry fixtures, not the new checker's logic."""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ARTIFICIAL-m5-seed-", dir=SCRATCH) as directory:
        base = Path(directory)
        package, old_expected = make_package(base / "geometry", "prepare")
        report = json.loads((package / "render-report.json").read_text(encoding="utf-8"))
        tracking = json.loads((package / "tracks.json").read_text(encoding="utf-8"))
        args, generator, receipt = make_receipt(base / "review")
        expected = {"schemaVersion":"pc3-full-animation-expectations-v1",
                    "sourceCommit":"a39cd664758575a81e1fcce437db245f60fc2c1b", "mode":"animation",
                    "settings":copy.deepcopy(SETTINGS), "generator":digest(generator),
                    "sourceDependencies":[digest(generator.with_name(name)) for name in DEPENDENCIES],
                    "layout":digest(args.layout), "fixture":digest(args.fixture),
                    "receipt":digest(args.animation_review), "reviewId":receipt["reviewId"],
                    "look":copy.deepcopy(old_expected["look"]),
                    "environmentDetail":copy.deepcopy(old_expected["environmentDetail"])}
        expected["verifiedFiles"] = []
        for role in ("generator","layout","fixture"):
            expected["verifiedFiles"].append({"role":role,**copy.deepcopy(receipt["sources"][role])})
        expected["verifiedFiles"] += [{"role":"dependency",**copy.deepcopy(item)} for item in receipt["sources"]["dependencies"]]
        for item in receipt["evidence"]["representatives"]+[receipt["evidence"]["shortReport"]]:
            expected["verifiedFiles"].append({key:copy.deepcopy(item[key]) for key in ("role","path","bytes","sha256")})
        # Current generator emits this gate metadata, not the receipt body.
        verified = verify_animation_review(args, generator)
        report.update(status="unreviewed-render-candidate", resolution=[1920,1080], renderedFrameCount=288,
                      generator=copy.deepcopy(expected["generator"]), layout=copy.deepcopy(expected["layout"]),
                      sourceDependencies=copy.deepcopy(expected["sourceDependencies"]),
                      fixture=copy.deepcopy(expected["fixture"]), threads={"requested":2,"actual":2,"mode":"FIXED"},
                      sceneReadback=expected_readback(),
                      animationReview={"requestedSha256":expected["receipt"]["sha256"],"verified":verified},
                      note="ARTIFICIAL M5 TEST: flat PNGs, fake blend and runtime claims; no pc1 approval.")
        tracking["resolution"] = [1920,1080]
        return report, tracking, expected, png(1920,1080)


def make_full_package(root):
    """New package with 288 complete CRC PNG files and external expectations."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    package = root / "package"
    package.mkdir()
    report, tracking, expected, image = copy.deepcopy(artificial_seed())
    write_json(package / "tracks.json", tracking)
    (package / "case-0002-ww3.blend").write_bytes(b"ARTIFICIAL M5 TEST, NOT A BLENDER FILE\n")
    report["rendered"] = []
    for frame in range(1,289):
        path = package / f"frame-{frame:04d}.png"
        path.write_bytes(image)
        report["rendered"].append({**digest(path),"frame":frame,"elapsedSeconds":(frame-1)/24,"renderSeconds":.01})
    report["tracks"], report["blend"] = digest(package / "tracks.json"), digest(package / "case-0002-ww3.blend")
    write_json(package / "render-report.json", report)
    return package, expected


class FullAnimationPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = importlib.import_module("verify_full_animation")
        SCRATCH.mkdir(parents=True, exist_ok=True)
        cls.originals = {}
        for path in [CHECKER, HERE / "build_scene.py", HERE / "verify_render_package.py", *[HERE/name for name in DEPENDENCIES]]:
            data = path.read_bytes()
            cls.originals[path] = data
            backup = SCRATCH / ("original-"+path.stem+"-"+hashlib.sha256(data).hexdigest()+".py")
            if not backup.exists():
                backup.write_bytes(data)
            if backup.read_bytes() != data:
                raise RuntimeError("Original backup differs; refusing overwrite")

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="ARTIFICIAL-m5-", dir=SCRATCH)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package, self.expected = make_full_package(self.root)
        self.report_original = (self.package / "render-report.json").read_bytes()
        self.tracks_original = (self.package / "tracks.json").read_bytes()

    def verify(self, package=None, expected=None):
        return self.validator.verify_full_animation(package or self.package, self.expected if expected is None else expected)

    def rejected(self, name, package=None, expected=None, message=None):
        result = self.verify(package, expected)
        self.assertIs(result["valid"], False, (name,result))
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(result["failures"], name)
        if message:
            self.assertIn(message, " ".join(f["detail"] for f in result["failures"]))
        for flag in ("visualAccepted","pixelDecoded","videoDecoded","authenticityVerified"):
            self.assertIs(result[flag], False)
        NEGATIVE_CASES.add(name)
        return result

    def report_cases(self, cases):
        for name, change in cases:
            with self.subTest(name=name):
                (self.package / "render-report.json").write_bytes(self.report_original)
                mutate_report(self.package, change)
                self.rejected(name)

    def track_cases(self, cases):
        for name, change in cases:
            with self.subTest(name=name):
                (self.package / "render-report.json").write_bytes(self.report_original)
                (self.package / "tracks.json").write_bytes(self.tracks_original)
                mutate_tracks(self.package, change)
                self.rejected(name)

    def test_complete_artificial_288_output_preserves_inputs_and_pending(self):
        before = {p.name:digest(p) for p in self.package.iterdir()}
        external_before = copy.deepcopy(self.expected)
        result = self.verify()
        self.assertIs(result["valid"], True, result)
        self.assertEqual(result["status"], "PASS_WITH_PENDING")
        self.assertEqual(result["failures"], [])
        self.assertTrue(result["pending"])
        self.assertEqual([r["frame"] for r in result["images"]], list(range(1,289)))
        self.assertEqual(result["images"][-1]["elapsedSeconds"], 287/24)
        self.assertEqual(len(result["inputDigests"]), 291)
        for flag in ("visualAccepted","pixelDecoded","videoDecoded","authenticityVerified"):
            self.assertIs(result[flag], False)
        self.assertEqual(before, {p.name:digest(p) for p in self.package.iterdir()})
        self.assertEqual(self.expected, external_before)

    def test_external_expectations_cannot_be_replaced_by_report_claims(self):
        cases = [("expected-empty",lambda e:e.clear()),
                 ("expected-schema",lambda e:e.update(schemaVersion="pc3-blender-candidate-v1")),
                 ("expected-source-commit",lambda e:e.update(sourceCommit="not-a-sha")),
                 ("expected-generator-sha",lambda e:e["generator"].update(sha256="0"*64)),
                 ("expected-layout-sha",lambda e:e["layout"].update(sha256="0"*64)),
                 ("expected-fixture-sha",lambda e:e["fixture"].update(sha256="0"*64)),
                 ("expected-receipt-sha",lambda e:e["receipt"].update(sha256="0"*64)),
                 ("expected-missing-receipt",lambda e:e.pop("receipt")),
                 ("expected-missing-dependency",lambda e:e["sourceDependencies"].pop()),
                 ("expected-duplicate-dependency",lambda e:e["sourceDependencies"].__setitem__(1,e["sourceDependencies"][0])),
                 ("expected-numeric-bool",lambda e:e["settings"].update(threads=True)),
                 ("expected-missing-verified-files",lambda e:e.pop("verifiedFiles")),
                 ("expected-duplicate-verified-file",lambda e:e["verifiedFiles"].append(copy.deepcopy(e["verifiedFiles"][0]))),
                 ("expected-verified-path-traversal",lambda e:e["verifiedFiles"][0].update(path="../build_scene.py"))]
        for name,change in cases:
            with self.subTest(name=name):
                expected = copy.deepcopy(self.expected)
                change(expected)
                self.rejected(name, expected=expected)
        self.rejected("report-as-expected", expected=json.loads(self.report_original))

    def test_report_flags_missing_metadata_units_events_and_source_bindings(self):
        cases = [("report-"+key,lambda r,k=key,v=value:r.__setitem__(k,v)) for key,value in
                 (("schemaVersion","old"),("synthetic",1),("mainRegistration",0),("visualGateAccepted",True),
                  ("videoEncoded",True),("fps","24"),("renderedFrameCount",72),("candidateFrameCount",True),
                  ("resolution",[1280,720]),("engine","CYCLES"),("requestedSamples",32),("cameraId","OTHER"))]
        cases += [("missing-"+key,lambda r,k=key:r.pop(k)) for key in
                  ("synthetic","mainRegistration","fixture","threads","sceneReadback","animationReview")]
        cases += [("report-other-event",lambda r:r["eventAnchor"].update(eventId="W-W2")),
                  ("report-other-date",lambda r:r["eventAnchor"].update(occurredAt="2026-09-19T02:33:00+09:00")),
                  ("report-tote-false",lambda r:r["eventAnchor"].update(businessToteId=False)),
                  ("report-fixture-sha",lambda r:r["fixture"].update(sha256="0"*64)),
                  ("report-generator-sha",lambda r:r["generator"].update(sha256="0"*64)),
                  ("report-module-sha",lambda r:r["sourceDependencies"][0].update(sha256="0"*64)),
                  ("report-module-duplicate",lambda r:r["sourceDependencies"].__setitem__(1,r["sourceDependencies"][0])),
                  ("report-runtime-null",lambda r:r["runtimeSamples"].update(value=None)),
                  ("report-runtime-bool",lambda r:r["runtimeSamples"].update(value=True)),
                  ("report-shadows-clamped",lambda r:r["shadowRays"].update(actual=2)),
                  ("report-shadow-applied-int",lambda r:r["shadowRays"].update(applied=1)),
                  ("report-threads-requested",lambda r:r["threads"].update(requested=4)),
                  ("report-threads-actual",lambda r:r["threads"].update(actual=4)),
                  ("report-threads-mode",lambda r:r["threads"].update(mode="AUTO"))]
        self.report_cases(cases)

    def test_receipt_verification_metadata_cannot_self_approve(self):
        cases = [("receipt-requested-sha",lambda r:r["animationReview"].update(requestedSha256="0"*64)),
                 ("receipt-unverified",lambda r:r["animationReview"].update(verified=None)),
                 ("receipt-approved-only",lambda r:r["animationReview"].update(verified={"approved":True})),
                 ("receipt-wrong-sha",lambda r:r["animationReview"]["verified"]["receipt"].update(sha256="0"*64)),
                 ("receipt-missing-files",lambda r:r["animationReview"]["verified"].pop("verifiedFiles")),
                 ("receipt-missing-dependency",lambda r:r["animationReview"]["verified"]["verifiedFiles"].pop(3)),
                 ("receipt-duplicate-file",lambda r:r["animationReview"]["verified"]["verifiedFiles"].append(copy.deepcopy(r["animationReview"]["verified"]["verifiedFiles"][0]))),
                 ("receipt-authenticated-int",lambda r:r["animationReview"]["verified"].update(issuerAuthenticated=0)),
                 ("receipt-visual-accepted",lambda r:r["animationReview"]["verified"].update(visualAccepted=True)),
                 ("receipt-traversal",lambda r:r["animationReview"]["verified"]["verifiedFiles"][0].update(path="../build_scene.py"))]
        self.report_cases(cases)

    def test_actual_readback_not_requested_values_is_enforced(self):
        cases = [("readback-"+key,lambda r,k=key,v=value:r["sceneReadback"].__setitem__(k,v)) for key,value in
                 (("engine","CYCLES"),("samples",32),("shadowRays",1),("threadsMode","AUTO"),("threads",4),
                  ("resolution",[1280,720]),("resolutionPercentage",50),("pixelAspect",[1,2]),
                  ("fps",30),("fpsBase",1.001),("frameStart",0),("frameEnd",72))]
        cases += [("readback-camera-"+key,lambda r,k=key,v=value:r["sceneReadback"]["camera"].__setitem__(k,v))
                  for key,value in (("name","OTHER"),("position",[25,1,8]),("forward",[0,0,-1]),("up",[0,0,1]),
                                    ("type","ORTHO"),("shift",[.1,0]),("lens",36),("sensorWidth",35),("sensorFit","VERTICAL"))]
        self.report_cases(cases)

    def test_exact_all_frame_order_names_counts_and_elapsed_clock(self):
        self.report_cases([
            ("duplicate-frame",lambda r:r["rendered"].__setitem__(132,r["rendered"][131])),
            ("missing-frame-row",lambda r:r["rendered"].pop()),
            ("previous-72-report",lambda r:r.update(rendered=r["rendered"][72:144],renderedFrameCount=72)),
            ("first-frame-bool",lambda r:r["rendered"][0].update(frame=True)),
            ("last-frame-time-12-not-287over24",lambda r:r["rendered"][-1].update(elapsedSeconds=12)),
            ("frame-name-order",lambda r:r["rendered"][0].update(name="frame-0288.png")),
            ("frame-time-unit",lambda r:r["rendered"][132].update(elapsedSeconds="5.5"))])

    def test_tracks_288_rows_event_camera_bbox_clock_and_required_fields(self):
        cases = [("track-"+key,lambda t,k=key,v=value:t.__setitem__(k,v)) for key,value in
                 (("source","AI detections"),("synthetic",1),("fps",30),("frameCount",72),("resolution",[1280,720]),
                  ("cameraId","OTHER"),("cameraPosition",[25,1,8]),("occlusionTested",0),("clippedFrames",[133]))]
        cases += [("tracks-row-missing",lambda t:t["frames"].pop()),
                  ("tracks-row-duplicate",lambda t:t["frames"].__setitem__(132,t["frames"][131])),
                  ("tracks-other-case",lambda t:t["eventAnchor"].update(caseId="CASE-0001")),
                  ("tracks-last-time-12",lambda t:t["frames"][-1].update(elapsedSeconds=12)),
                  ("tracks-missing-bbox",lambda t:t["frames"][132].pop("bboxNormalizedXYXY")),
                  ("tracks-first-frame-bool",lambda t:t["frames"][0].update(frame=True)),
                  ("tracks-tote-false",lambda t:t["frames"][132].update(businessToteId=False))]
        cases += [("bbox-"+str(i),lambda t,v=value:t["frames"][132].update(bboxNormalizedXYXY=v)) for i,value in
                  enumerate(([-.1,.2,.4,.6],[.1,.2,1.1,.6],[.5,.5,.4,.6],[True,.2,.4,.6],[.1,.2,.4]))]
        self.track_cases(cases)

    def test_rejects_png_hash_mismatch(self):
        mutate_report(self.package,lambda r:r["rendered"][132].update(sha256="0"*64))
        self.rejected("png-hash-mismatch")

    def test_receipt_cannot_alias_its_own_fixture_reference(self):
        self.expected["receipt"]["name"] = "cases.json"
        for item in self.expected["verifiedFiles"]:
            if item["role"] == "fixture":
                item["path"] = "cases.json"
        def change(report):
            report["animationReview"]["verified"]["receipt"]["name"] = "cases.json"
            report["animationReview"]["verified"]["verifiedFiles"] = copy.deepcopy(self.expected["verifiedFiles"])
        mutate_report(self.package,change)
        self.rejected("receipt-self-path-collision")

    def test_input_changed_after_its_read_is_rejected_by_final_stamp(self):
        original_reader = self.validator.common._file
        changed = False
        def reader(directory,name,*args,**kwargs):
            nonlocal changed
            output = original_reader(directory,name,*args,**kwargs)
            if name == "frame-0133.png" and not changed:
                changed = True
                (self.package/"render-report.json").write_bytes(self.report_original+b"\n ")
            return output
        try:
            with mock.patch.object(self.validator.common,"_file",reader):
                self.rejected("input-changed-after-first-read",message="Package changed")
            self.assertTrue(changed)
        finally:
            (self.package/"render-report.json").write_bytes(self.report_original)

    def test_disabled_png_hash_guard_is_killed_by_independent_negative(self):
        source = self.originals[CHECKER]
        tree, changed = ast.parse(source), 0
        for node in ast.walk(tree):
            if (isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id == "require"
                    and len(node.args)>1 and isinstance(node.args[1],ast.Constant)
                    and node.args[1].value == "PNG bytes or SHA256 differ from the report."):
                node.args[0] = ast.Constant(True)
                changed += 1
        self.assertEqual(changed,1,"Mutation must target exactly the actual PNG hash check")
        mutant = types.ModuleType("_m5_artificial_png_sha_mutant")
        mutant.__file__ = str(CHECKER)
        exec(compile(ast.fix_missing_locations(tree),"<in-memory-disabled-png-sha>","exec"),mutant.__dict__)
        result = unittest.TestResult()
        with mock.patch.object(self.validator,"verify_full_animation",mutant.verify_full_animation):
            FullAnimationPackageTests("test_rejects_png_hash_mismatch").run(result)
        self.assertEqual(result.testsRun,1)
        self.assertEqual(len(result.errors),0,result.errors)
        self.assertEqual(len(result.failures),1,"PNG hash mutant survived its independent negative")
        self.assertIn("True is not False",result.failures[0][1])
        MUTATIONS.append({"name":"disable-PNG-byte-and-SHA-guard-in-memory","killed":True,
                          "negativeTest":"test_rejects_png_hash_mismatch","testsRun":1,
                          "failures":1,"errors":0,"actualAssertionFailure":result.failures[0][1],
                          "sourceFilesChanged":False})
        self.assertEqual(CHECKER.read_bytes(),source)

    def test_missing_byte_tampered_and_structurally_corrupt_files(self):
        for name in ("frame-0133.png","tracks.json","case-0002-ww3.blend","render-report.json"):
            path = self.package/name
            data = path.read_bytes()
            with self.subTest(missing=name):
                path.unlink(); self.rejected("missing-"+name)
            path.write_bytes(data)
        path = self.package/"frame-0133.png"
        original = path.read_bytes()
        path.write_bytes(original+b"TAMPER")
        self.rejected("png-byte-tamper")
        broken = [("resolution-720",png()),("truncated-iend",original[:-12]),
                  ("crc",original[:29]+bytes([original[29]^1])+original[30:]),("trailing-bytes",original+b"x")]
        for name,data in broken:
            with self.subTest(name=name):
                path.write_bytes(data)
                update_asset_digest(self.package,path.name)
                self.rejected("png-structure-"+name)

    def test_descriptor_paths_extra_files_and_strict_json(self):
        self.report_cases([(name,lambda r,v=value:r["rendered"][0].update(name=v)) for name,value in
                           (("path-traversal","../frame-0001.png"),("path-absolute",str(self.root/"outside.png")),
                            ("path-backslash","nested\\frame-0001.png"))])
        (self.package/"render-report.json").write_bytes(self.report_original)
        extra = self.package/"frame-0289.png"; extra.write_bytes(png())
        self.rejected("unexpected-289th-frame"); extra.unlink()
        for name,data in (("duplicate-key",b'{"synthetic":true,'+self.report_original[1:]),
                          ("nan",self.report_original.replace(b'"wallSeconds": 0.1',b'"wallSeconds": NaN')),
                          ("infinity",self.report_original.replace(b'"wallSeconds": 0.1',b'"wallSeconds": Infinity')),
                          ("malformed",b'{broken')):
            with self.subTest(name=name):
                (self.package/"render-report.json").write_bytes(data)
                self.rejected("json-"+name)

    def test_hardlink_asset_rejected_by_actual_link_guard(self):
        asset = self.package/"frame-0133.png"
        outside = self.root/"outside-original.png"
        original = asset.read_bytes(); outside.write_bytes(original); asset.unlink()
        try:
            os.link(outside,asset)
            self.assertGreater(asset.stat().st_nlink,1)
            self.rejected("hardlink-asset",message="Hard-linked")
            self.assertEqual(outside.read_bytes(),original)
        finally:
            if asset.exists(): asset.unlink()

    def test_junction_package_rejected_by_actual_reparse_guard(self):
        linked = self.root/"junction-package"
        if os.name == "nt":
            done = subprocess.run(["cmd","/c","mklink","/J",str(linked),str(self.package)],capture_output=True,text=True)
            if done.returncode: self.skipTest("OS refused isolated junction creation; no privilege changes")
        else: linked.symlink_to(self.package,target_is_directory=True)
        try:
            self.rejected("junction-package",package=linked,message="link/reparse")
            self.assertEqual((self.package/"render-report.json").read_bytes(),self.report_original)
        finally:
            self.assertEqual(linked.parent.resolve(),self.root.resolve())
            if linked.is_symlink(): linked.unlink()
            elif linked.is_junction(): linked.rmdir()

    def test_symlink_asset_rejected_if_os_permits_creation(self):
        asset = self.package/"frame-0133.png"
        outside = self.root/"outside-original.png"
        original = asset.read_bytes(); outside.write_bytes(original); asset.unlink()
        try:
            try: asset.symlink_to(outside)
            except OSError as error: self.skipTest(f"OS refused symlink creation; no privilege changes: {error}")
            self.rejected("symlink-asset",message="link/reparse")
        finally:
            if asset.is_symlink(): asset.unlink()

    def test_cli_external_expected_and_read_only_input(self):
        expected_path = self.root/"external-expectations.json"; write_json(expected_path,self.expected)
        argv = [sys.executable,"-B",str(CHECKER),"--package",str(self.package),"--expectations",str(expected_path)]
        before = {p.name:digest(p) for p in self.package.iterdir()}
        completed = subprocess.run(argv,capture_output=True,text=True)
        self.assertEqual(completed.returncode,0,completed.stdout+completed.stderr)
        self.assertIs(json.loads(completed.stdout)["valid"],True)
        self.assertEqual(before,{p.name:digest(p) for p in self.package.iterdir()})
        self.assertEqual(json.loads(expected_path.read_bytes()),self.expected)
        inside = self.package/"self-expectations.json"; write_json(inside,self.expected)
        result = subprocess.run(argv[:-1]+[str(inside)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        failure = json.loads(result.stdout)
        self.assertIn("outside", " ".join(f["detail"] for f in failure["failures"]))
        NEGATIVE_CASES.add("cli-self-contained-expectations")
        self.assertEqual((self.package/"render-report.json").read_bytes(),self.report_original)

    def test_original_sources_are_byte_preserved(self):
        for path,data in self.originals.items():
            self.assertEqual(path.read_bytes(),data,str(path))


if __name__ == "__main__":
    unittest.main()
