"""Independent M6 packaging tests: subprocesses and MP4 bytes are artificial.

The real M5 verifier checks a 291-file synthetic fixture. A fake subprocess then
emits probe/framehash protocol data and minimal MP4 boxes. These tests do not
encode/decode video, authenticate a receipt, or accept visual/product quality.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SCRATCH = ROOT / ".local/pc3-m6-review"
PACKAGER = HERE / "package_full_animation_media.py"
sys.path.insert(0,str(HERE))
from test_full_animation_package import make_full_package
from test_render_package import digest, write_json, mutate_report

NEGATIVE_CASES = set()
MUTATIONS = []
PROCESS_CALLS = []
COMPOUND_OBSERVATIONS = []
IDENTITY_MATRIX = (65536,0,0,0,65536,0,0,0,1073741824)


def fake_mp4(faststart=True,*,width=1920,height=1080,frames=288,movie_duration=12000,media_duration=147456,
             movie_matrix=IDENTITY_MATRIX,track_matrix=IDENTITY_MATRIX,movie_version=0,track_version=0,
             omit_tkhd=False,movie_truncate=None,track_truncate=None,sample_children=()):
    """Independent clock/display/sample-box data; not a decodable MP4."""
    def box(kind,payload):
        return struct.pack(">I",8+len(payload))+kind+payload
    ftyp=box(b"ftyp",b"isom\0\0\0\0isomiso2avc1mp41")
    movie=bytearray(112 if movie_version==1 else 100)
    movie[0]=movie_version
    if movie_version==1:
        struct.pack_into(">IQ",movie,20,1000,movie_duration); matrix_offset=48
    else:
        struct.pack_into(">II",movie,12,1000,movie_duration); matrix_offset=36
    struct.pack_into(">9i",movie,matrix_offset,*movie_matrix)
    mvhd=box(b"mvhd",bytes(movie[:movie_truncate]))
    track=bytearray(96 if track_version==1 else 84)
    track[0],track[3]=track_version,7
    if track_version==1:
        struct.pack_into(">I",track,20,1); struct.pack_into(">Q",track,28,movie_duration); track_offset=52
    else:
        struct.pack_into(">II",track,12,1,0); struct.pack_into(">I",track,20,movie_duration); track_offset=40
    struct.pack_into(">9iII",track,track_offset,*track_matrix,width<<16,height<<16)
    tkhd=b"" if omit_tkhd else box(b"tkhd",bytes(track[:track_truncate]))
    mdhd=box(b"mdhd",bytes(12)+struct.pack(">II",12288,media_duration)+bytes(4))
    hdlr=box(b"hdlr",bytes(8)+b"vide"+bytes(12)+b"ARTIFICIAL HANDLER\0")
    sample=bytearray(78)
    struct.pack_into(">H",sample,6,1)
    struct.pack_into(">HH",sample,24,width,height)
    extensions=b"".join(box(kind,data) for kind,data in sample_children)
    stsd=box(b"stsd",bytes(4)+struct.pack(">I",1)+box(b"avc1",bytes(sample)+extensions))
    stts=box(b"stts",bytes(4)+struct.pack(">III",1,frames,512))
    stbl=box(b"stbl",stsd+stts)
    moov=box(b"moov",mvhd+box(b"trak",tkhd+box(b"mdia",mdhd+hdlr+box(b"minf",stbl))))
    mdat=box(b"mdat",b"ARTIFICIAL TEST PAYLOAD NOT VIDEO")
    return ftyp+(moov+mdat if faststart else mdat+moov)


def probe_data():
    return {"streams":[{"index":0,"codec_type":"video","codec_name":"h264","width":1920,"height":1080,
                        "pix_fmt":"yuv420p","avg_frame_rate":"24/1","r_frame_rate":"24/1",
                        "nb_frames":"288","nb_read_frames":"288","duration":"12.000000",
                        "start_time":"0.000000","time_base":"1/12288","start_pts":0,"duration_ts":147456}],
            "format":{"nb_streams":1,"duration":"12.000000","start_time":"0.000000",
                      "format_name":"mov,mp4,m4a,3gp,3g2,mj2"}}


def framehash_data(count=288):
    header=("#format: frame checksums\n#version: 2\n#hash: SHA256\n#software: ARTIFICIAL TEST PROTOCOL\n"
            "#tb 0: 1/24\n#media_type 0: video\n#codec_id 0: rawvideo\n#dimensions 0: 1920x1080\n#sar 0: 1/1\n"
            "#stream#, dts, pts, duration, size, hash\n")
    return (header+"".join(f"0, {i}, {i}, 1, 3110400, {hashlib.sha256(('FAKE FRAME '+str(i)).encode()).hexdigest()}\n"
                            for i in range(count))).encode("ascii")


def input_metadata():
    return ("Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'ARTIFICIAL sorter-demo.mp4':\n"
            "  Metadata:\n    comment : ARTIFICIAL TEST, NO VIDEO PROCESSED\n"
            "  Duration: 00:00:12.00, start: 0.000000, bitrate: 123 kb/s\n"
            "  Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(progressive), "
            "1920x1080 [SAR 1:1 DAR 16:9], 100 kb/s, 24 fps, 24 tbr, 12288 tbn (default)\n"
            "Stream mapping:\n  Stream #0:0 -> #0:0 (h264 (native) -> rawvideo (native))\n"
            "Output #0, framehash, to 'pipe:1':\n"
            "  Stream #0:0(und): Video: rawvideo, yuv420p, 1920x1080, 24 fps, 24 tbn\n").encode("utf-8")


def matrix_text(matrix):
    return "\n"+"\n".join(f"{row:08d}: "+" ".join(str(v) for v in matrix[row*3:row*3+3]) for row in range(3))+"\n"


def text_rotation(value):
    return input_metadata().replace(b"Stream mapping:",
        ("    Side data:\n      displaymatrix: rotation of "+value+" degrees\nStream mapping:").encode("utf-8"))


class FakeProcesses:
    """Record actual subprocess calls; never invoke an executable."""
    def __init__(self,ffmpeg,ffprobe):
        self.ffmpeg,self.ffprobe=str(ffmpeg),str(ffprobe)
        self.probe=probe_data()
        self.framehash=framehash_data()
        self.metadata=input_metadata()
        self.video=fake_mp4()
        self.calls=[]
        self.failure=None
        self.after_encode=None
        self.after_decode=None

    def __call__(self,argv,**kwargs):
        args=list(map(str,argv))
        if "-version" in args:
            stage="version"
        elif args[0] == self.ffprobe:
            stage="probe"
        elif "framehash" in args:
            stage="decode"
        else:
            stage="encode"
        self.calls.append({"stage":stage,"argv":args,"options":copy.copy(kwargs)})
        PROCESS_CALLS.append({"stage":stage,"shell":kwargs.get("shell"),"timeout":kwargs.get("timeout"),
                              "creationflags":kwargs.get("creationflags",0),"capture_output":kwargs.get("capture_output"),
                              "text":kwargs.get("text",False),"encoding":kwargs.get("encoding")})
        if self.failure == stage+"-timeout":
            raise subprocess.TimeoutExpired(args,kwargs.get("timeout",600),output=b"partial",stderr=b"timeout")
        if stage == "version":
            out=b"ARTIFICIAL ffmpeg protocol fixture; no binary executed\n"
        elif stage == "encode":
            # Actual output path must be explicit; no shell parsing is emulated.
            Path(args[-1]).write_bytes(self.video)
            if self.after_encode: self.after_encode()
            out=b""
        elif stage == "probe":
            out=self.probe if isinstance(self.probe,bytes) else json.dumps(self.probe).encode("utf-8")
        else:
            out=self.framehash
            if self.after_decode: self.after_decode()
        if self.failure == stage+"-exit":
            code,err=1,"인공 실패: 성공 문구가 있어도 실패".encode("utf-8")
        else:
            code,err=0,self.metadata if stage=="decode" else b"ARTIFICIAL TEST; no actual video processing\n"
        if kwargs.get("text") or kwargs.get("encoding"):
            # Match subprocess.run's documented text conversion without running it.
            encoding=kwargs.get("encoding") or "utf-8"
            out,err=out.decode(encoding,kwargs.get("errors","strict")),err.decode(encoding,kwargs.get("errors","strict"))
        return subprocess.CompletedProcess(args,code,out,err)


class FullAnimationMediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packager=importlib.import_module("package_full_animation_media")
        SCRATCH.mkdir(parents=True,exist_ok=True)
        cls.originals={}
        for name in ("package_full_animation_media.py","verify_full_animation.py","verify_render_package.py",
                     "full_render_gate.py","build_scene.py","scene_contract.py","look_presets.py",
                     "environment_detail.py","shadow_settings.py"):
            path=HERE/name; data=path.read_bytes(); cls.originals[path]=data
            backup=SCRATCH/("original-"+path.stem+"-"+hashlib.sha256(data).hexdigest()+".py")
            if not backup.exists(): backup.write_bytes(data)
            if backup.read_bytes()!=data: raise RuntimeError("Original source backup differs")

    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix="ARTIFICIAL-m6-",dir=SCRATCH)
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.package,self.expected=make_full_package(self.root/"source")
        # These harmless original bytes must survive copying, not reserialization.
        tracks=self.package/"tracks.json"
        tracks.write_bytes(tracks.read_bytes()+b" \n\t\n")
        mutate_report(self.package,lambda r:r.update(tracks=digest(tracks)))
        self.expected_path=self.root/"external-expected.json"
        write_json(self.expected_path,self.expected)
        (self.root/"tools").mkdir()
        self.ffmpeg,self.ffprobe=self.root/"tools/fake-ffmpeg.exe",self.root/"tools/fake-ffprobe.exe"
        self.ffmpeg.write_bytes(b"ARTIFICIAL TEST FILE; NEVER EXECUTED")
        self.ffprobe.write_bytes(b"ARTIFICIAL TEST FILE; NEVER EXECUTED")
        self.output=self.root/"new-output"
        self.processes=FakeProcesses(self.ffmpeg,self.ffprobe)

    def run_package(self,output=None,**kwargs):
        probe=kwargs.pop("ffprobe",None)
        with mock.patch.object(self.packager.subprocess,"run",self.processes):
            return self.packager.package_full_animation(self.package,self.expected_path,output or self.output,
                                                        self.ffmpeg,probe,**kwargs)

    def rejected(self,name,output=None,**kwargs):
        output=output or self.output
        result=self.run_package(output=output,**kwargs)
        self.assertIs(result["valid"],False,(name,result))
        self.assertEqual(result["status"],"FAIL")
        self.assertTrue(result["failures"])
        for flag in ("visualAccepted","mainRegistration","authenticityVerified"):
            self.assertIs(result[flag],False)
        if output.is_dir() and output!=self.package:
            self.assertFalse((output/"candidate-report.json").exists())
            # Leftover partial/staged/descriptor files are not success. Cleanup
            # permission is not the acceptance boundary: the consumer must reject.
            self.assertIs(self.packager.validate_candidate(output)["valid"],False)
        NEGATIVE_CASES.add(name)
        return result

    def test_normal_preflight_encode_decode_raw_copy_and_exact_five_field_descriptor(self):
        before={p.name:digest(p) for p in self.package.iterdir()}
        expected_before=self.expected_path.read_bytes()
        result=self.run_package()
        self.assertIs(result["valid"],True,result)
        self.assertEqual(result["status"],"PASS_WITH_PENDING")
        self.assertIs(result["encoded"],True)
        self.assertIs(result["videoDecoded"],True)
        for flag in ("visualAccepted","mainRegistration","authenticityVerified"):
            self.assertIs(result[flag],False)
        self.assertEqual([c["stage"] for c in self.processes.calls if c["stage"]!="version"],["encode","decode"])
        self.assertEqual({p.name for p in self.output.iterdir()},
                         {"sorter-demo.mp4","sorter-demo.tracks.json","sorter-demo.tracks.descriptor.json","candidate-report.json"})
        self.assertEqual((self.output/"sorter-demo.tracks.json").read_bytes(),(self.package/"tracks.json").read_bytes())
        descriptor=json.loads((self.output/"sorter-demo.tracks.descriptor.json").read_bytes())
        tracks=digest(self.output/"sorter-demo.tracks.json")
        self.assertEqual(descriptor,{"schemaVersion":"oneflow-cctv-tracks-v1","url":"/demo/sorter-demo.tracks.json",
                                     "bytes":tracks["bytes"],"sha256":tracks["sha256"],
                                     "videoSha256":digest(self.output/"sorter-demo.mp4")["sha256"]})
        self.assertEqual(before,{p.name:digest(p) for p in self.package.iterdir()})
        self.assertEqual(expected_before,self.expected_path.read_bytes())
        self.assertIs(self.packager.validate_candidate(self.output)["valid"],True)

    def test_subprocess_uses_explicit_argv_timeout_utf8_capture_hidden_windows_and_full_decode(self):
        result=self.run_package(timeout=31)
        self.assertIs(result["valid"],True,result)
        for call in self.processes.calls:
            options=call["options"]
            self.assertIs(options.get("shell"),False)
            self.assertEqual(options.get("timeout"),31)
            self.assertIs(options.get("capture_output"),True)
            self.assertTrue(not options.get("text") or bool(options.get("encoding")),"Host cp949 must not decode UTF-8 implicitly")
            if os.name=="nt":
                self.assertTrue(options.get("creationflags",0)&subprocess.CREATE_NO_WINDOW)
        encode=next(c["argv"] for c in self.processes.calls if c["stage"]=="encode")
        for option,value in (("-framerate","24"),("-start_number","1"),("-frames:v","288"),
                             ("-c:v","libx264"),("-pix_fmt","yuv420p"),("-aspect","16:9"),("-movflags","+faststart")):
            self.assertIn(option,encode)
            self.assertEqual(encode[encode.index(option)+1],value)
        self.assertIn("-n",encode)
        self.assertTrue(any(arg.endswith("frame-%04d.png") for arg in encode))
        self.assertFalse(set(encode)&{"-ss","-t","-itsoffset","-vf","-filter:v","-filter_complex","-y"})
        decode=next(c["argv"] for c in self.processes.calls if c["stage"]=="decode")
        self.assertFalse(set(decode)&{"-ss","-t","-frames:v","-vframes"},"Full decode must not hide trailing frames")

    def test_m5_failure_stops_before_any_encoder_and_has_no_success_outputs(self):
        (self.package/"frame-0133.png").unlink()
        self.rejected("m5-missing-frame")
        self.assertEqual(self.processes.calls,[])

    def test_nonzero_exit_and_timeouts_never_publish_success(self):
        for stage in ("encode","probe","decode"):
            for kind in ("exit","timeout"):
                name=stage+"-"+kind
                with self.subTest(name=name):
                    self.processes.failure=name
                    self.rejected(name,output=self.root/("out-"+name),ffprobe=self.ffprobe)
        self.processes.failure="encode-exit"
        failed=self.root/"partial-encode"
        self.rejected("partial-encode",output=failed)
        self.processes.failure=None
        before=len(self.processes.calls)
        self.rejected("failed-output-cannot-be-reused",output=failed)
        self.assertEqual(len(self.processes.calls),before)

    def test_probe_framecount_duration_resolution_codec_pixfmt_and_stream_identity(self):
        cases=[("frames287","nb_read_frames","287"),("declared-frames72","nb_frames","72"),
               ("duration3","duration","3.0"),("width1280","width",1280),("height720","height",720),
               ("codec-hevc","codec_name","hevc"),("pixel-yuv444p","pix_fmt","yuv444p"),
               ("fps30","avg_frame_rate","30/1"),("rate30","r_frame_rate","30/1"),
               ("offset","start_time","0.041667"),("width-bool","width",True)]
        for name,field,value in cases:
            with self.subTest(name=name):
                self.processes.probe=probe_data(); self.processes.probe["streams"][0][field]=value
                self.rejected("probe-"+name,output=self.root/("out-"+name),ffprobe=self.ffprobe)
        for name,change in (("format-duration",lambda p:p["format"].update(duration="3.0")),
                            ("extra-audio",lambda p:p["streams"].append({"codec_type":"audio","codec_name":"aac"})),
                            ("missing-streams",lambda p:p.pop("streams"))):
            with self.subTest(name=name):
                self.processes.probe=probe_data(); change(self.processes.probe)
                self.rejected("probe-"+name,output=self.root/("out-"+name),ffprobe=self.ffprobe)

    def test_optional_ffprobe_success_and_ffmpeg_only_input_metadata_rejections(self):
        result=self.run_package(output=self.root/"with-probe",ffprobe=self.ffprobe)
        self.assertIs(result["valid"],True,result)
        self.assertIn("probe",[c["stage"] for c in self.processes.calls])
        good=input_metadata()
        cases=[("missing",b""),("success-text-only",b"Successfully decoded all 288 frames"),
               ("wrong-input-codec",good.replace(b"Video: h264",b"Video: hevc")),
               ("wrong-input-pixfmt",good.replace(b"yuv420p(progressive)",b"yuv444p(progressive)")),
               ("wrong-input-width",good.replace(b"1920x1080 [SAR",b"1280x720 [SAR")),
               ("wrong-input-fps",good.replace(b"24 fps, 24 tbr",b"30 fps, 24 tbr")),
               ("wrong-input-tbr",good.replace(b"24 fps, 24 tbr",b"24 fps, 30 tbr")),
               ("wrong-input-start",good.replace(b"start: 0.000000",b"start: 0.041667")),
               ("wrong-input-duration",good.replace(b"00:00:12.00",b"00:00:03.00")),
               ("output-cannot-substitute-input",good.split(b"Output #0",1)[1])]
        for name,data in cases:
            with self.subTest(name=name):
                self.processes.metadata=data
                self.rejected("ffmpeg-metadata-"+name,output=self.root/("out-"+name))

    def test_rejects_wrong_decoded_frame_count(self):
        self.processes.framehash=framehash_data(287)
        self.rejected("decode-287-frames")

    def test_missing_input_and_decoded_sample_aspect_are_rejected(self):
        cases=[("input-sar-absent",input_metadata().replace(b" [SAR 1:1 DAR 16:9]",b""),framehash_data()),
               ("decoded-sar-zero",input_metadata(),framehash_data().replace(b"#sar 0: 1/1",b"#sar 0: 0/1"))]
        for name,metadata,frames in cases:
            with self.subTest(name=name):
                self.processes.metadata,self.processes.framehash=metadata,frames
                self.rejected(name,output=self.root/("out-"+name))

    def test_disabled_full_decode_guard_is_killed_by_independent_negative(self):
        source=self.originals[PACKAGER]
        tree,changed=ast.parse(source),0
        for node in ast.walk(tree):
            if (isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=="require"
                    and len(node.args)>1 and isinstance(node.args[1],ast.Constant)
                    and node.args[1].value=="Full decode must yield exactly 288 1080p yuv420p frames at 24 fps."):
                node.args[0]=ast.Constant(True)
                changed+=1
        self.assertEqual(changed,1,"Mutation must disable exactly the actual full decode gate")
        mutant=types.ModuleType("_m6_artificial_disabled_full_decode")
        mutant.__file__=str(PACKAGER)
        exec(compile(ast.fix_missing_locations(tree),"<in-memory-disabled-full-decode>","exec"),mutant.__dict__)
        result=unittest.TestResult()
        with mock.patch.object(self.packager,"package_full_animation",mutant.package_full_animation):
            FullAnimationMediaTests("test_rejects_wrong_decoded_frame_count").run(result)
        self.assertEqual(result.testsRun,1)
        self.assertEqual(len(result.errors),0,result.errors)
        self.assertEqual(len(result.failures),1,"Full decode mutant survived")
        self.assertIn("True is not False",result.failures[0][1])
        MUTATIONS.append({"name":"disable-exact288-full-decode-guard-in-memory","killed":True,
                          "negativeTest":"test_rejects_wrong_decoded_frame_count","testsRun":1,
                          "failures":1,"errors":0,"actualAssertionFailure":result.failures[0][1],
                          "sourceFilesChanged":False})
        self.assertEqual(PACKAGER.read_bytes(),source)

    def test_decode_all_frames_clock_dimensions_hashes_and_errors(self):
        good=framehash_data()
        cases=[("extra-frame",framehash_data(289)),("empty",b""),("malformed",b"success; 288 frames\n"),
               ("bad-timebase",good.replace(b"#tb 0: 1/24",b"#tb 0: 1/30")),
               ("bad-size",good.replace(b"#dimensions 0: 1920x1080",b"#dimensions 0: 1280x720")),
               ("duplicate-pts",good.replace(b"0, 132, 132, 1,",b"0, 131, 131, 1,")),
               ("late-offset",good.replace(b"0, 287, 287, 1,",b"0, 288, 288, 1,")),
               ("wrong-duration",good.replace(b"0, 132, 132, 1,",b"0, 132, 132, 2,")),
               ("wrong-hash",good.replace(hashlib.sha256(b"FAKE FRAME 132").hexdigest().encode(),b"not-a-sha"))]
        for name,data in cases:
            with self.subTest(name=name):
                self.processes.framehash=data
                self.rejected("decode-"+name,output=self.root/("out-"+name))

    def test_mp4_requires_faststart_and_complete_boxes(self):
        for name,data in (("moov-after-mdat",fake_mp4(False)),("empty",b""),
                          ("truncated",fake_mp4()[:-2]),("not-mp4",b"successfully encoded video"),
                          ("movie-duration",fake_mp4(movie_duration=3000)),
                          ("media-duration",fake_mp4(media_duration=36864)),
                          ("width",fake_mp4(width=1280)),("sample-count",fake_mp4(frames=72))):
            with self.subTest(name=name):
                self.processes.video=data
                self.rejected("mp4-"+name,output=self.root/("out-"+name))

    def test_source_or_external_expected_change_after_preflight_is_rejected(self):
        source=self.package/"tracks.json"
        before=source.read_bytes()
        self.processes.after_encode=lambda:source.write_bytes(before+b"\nCHANGED")
        try:
            self.rejected("source-changed-after-preflight",output=self.root/"source-changed")
        finally:
            source.write_bytes(before)
        original=self.expected_path.read_bytes()
        self.processes.after_encode=lambda:self.expected_path.write_bytes(original+b"\n ")
        try:
            self.rejected("expected-changed-after-preflight",output=self.root/"expected-changed")
        finally:
            self.expected_path.write_bytes(original)

    def test_video_change_during_validation_is_rejected(self):
        def change_video():
            path=Path(next(c["argv"][-1] for c in self.processes.calls if c["stage"]=="encode"))
            path.write_bytes(path.read_bytes()+b"CHANGED AFTER DECODE")
        self.processes.after_decode=change_video
        self.rejected("video-changed-during-validation")

    def test_late_staged_report_write_failure_is_not_published_or_accepted(self):
        original_writer=self.packager._write_new
        def fail_after_report(directory,name,data,*args,**kwargs):
            result=original_writer(directory,name,data,*args,**kwargs)
            if name=="candidate-report.staged.json":
                raise OSError("ARTIFICIAL injected late write failure")
            return result
        with mock.patch.object(self.packager,"_write_new",fail_after_report):
            self.rejected("late-report-write-failure")
        self.assertTrue((self.output/"failure.json").is_file())

    def test_final_video_tamper_after_tracks_copy_is_rejected_before_publication(self):
        original_writer=self.packager._write_new
        for target_name in ("sorter-demo.mp4","sorter-demo.tracks.json"):
            with self.subTest(target=target_name):
                changed=False
                def tamper_after_tracks(directory,name,data,*args,**kwargs):
                    nonlocal changed
                    result=original_writer(directory,name,data,*args,**kwargs)
                    if name=="sorter-demo.tracks.json":
                        target=Path(directory)/target_name
                        target.write_bytes(target.read_bytes()+b"ARTIFICIAL LATE OUTPUT TAMPER")
                        changed=True
                    return result
                with mock.patch.object(self.packager,"_write_new",tamper_after_tracks):
                    self.rejected("final-output-tamper-"+target_name,output=self.root/("late-"+target_name))
                self.assertTrue(changed)

    def replace_owned_output_with_foreign_directory(self,directory):
        directory=Path(directory)
        retained=self.root/"owned-output-retained"
        # Verify both absolute destinations before this isolated directory move.
        self.assertEqual(directory.resolve().parent,self.root.resolve())
        self.assertEqual(retained.absolute().parent,self.root.resolve())
        self.assertFalse(retained.exists())
        old_identity=directory.stat().st_dev,directory.stat().st_ino
        directory.rename(retained)
        directory.mkdir()
        self.assertNotEqual(old_identity,(directory.stat().st_dev,directory.stat().st_ino))
        (directory/"FOREIGN-SENTINEL").write_bytes(b"MUST REMAIN THE ONLY FOREIGN FILE")

    def test_output_inode_replacement_before_publication_is_rejected(self):
        original_writer=self.packager._write_new
        replaced=False
        def replace_after_tracks(directory,name,data,*args,**kwargs):
            nonlocal replaced
            result=original_writer(directory,name,data,*args,**kwargs)
            if name=="sorter-demo.tracks.json":
                self.replace_owned_output_with_foreign_directory(directory)
                replaced=True
            return result
        with mock.patch.object(self.packager,"_write_new",replace_after_tracks):
            self.rejected("output-inode-replacement-before-publication")
        self.assertTrue(replaced)
        self.assertEqual({p.name for p in self.output.iterdir()},{"FOREIGN-SENTINEL"})

    def test_failure_does_not_write_into_replacement_foreign_directory(self):
        original_writer=self.packager._write_new
        replaced=False
        def replace_then_fail(directory,name,data,*args,**kwargs):
            nonlocal replaced
            result=original_writer(directory,name,data,*args,**kwargs)
            if name=="sorter-demo.tracks.json":
                self.replace_owned_output_with_foreign_directory(directory)
                replaced=True
                raise OSError("ARTIFICIAL failure after foreign directory replacement")
            return result
        with mock.patch.object(self.packager,"_write_new",replace_then_fail):
            self.rejected("failure-after-output-inode-replacement")
        self.assertTrue(replaced)
        self.assertEqual({p.name for p in self.output.iterdir()},{"FOREIGN-SENTINEL"},
                         "Failure reporting must not write into a replacement foreign directory")

    def test_output_existing_overlap_traversal_and_binary_missing_do_not_encode(self):
        existing=self.root/"existing"; existing.mkdir(); (existing/"sentinel").write_bytes(b"KEEP")
        empty=self.root/"existing-empty"; empty.mkdir()
        for name,target in (("existing",existing),("empty-existing",empty),("source-overlap",self.package),
                            ("source-child",self.package/"encoded"),("source-parent",self.package.parent),
                            ("traversal",self.root/"not-created"/".."/"escape")):
            with self.subTest(name=name):
                self.rejected("output-"+name,output=target)
        self.assertEqual((existing/"sentinel").read_bytes(),b"KEEP")
        self.assertEqual({p.name for p in existing.iterdir()},{"sentinel"})
        self.assertEqual(list(empty.iterdir()),[])
        self.assertEqual({p.name for p in self.package.parent.iterdir()},{"package"})
        self.ffmpeg.unlink()
        self.rejected("missing-explicit-ffmpeg")
        self.assertEqual(self.processes.calls,[])

    def test_output_under_junction_parent_is_rejected(self):
        target=self.root/"outside-dir"; target.mkdir()
        linked=self.root/"linked-parent"
        if os.name=="nt":
            done=subprocess.run(["cmd","/c","mklink","/J",str(linked),str(target)],capture_output=True,
                                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            if done.returncode: self.skipTest("OS refused isolated junction; no privilege changes")
        else: linked.symlink_to(target,target_is_directory=True)
        try:
            result=self.rejected("output-junction",output=linked/"result")
            self.assertTrue(any("link" in f["detail"].lower() or "reparse" in f["detail"].lower() for f in result["failures"]))
            self.assertEqual(list(target.iterdir()),[])
            self.assertEqual(self.processes.calls,[])
        finally:
            self.assertEqual(linked.parent.resolve(),self.root.resolve())
            if linked.is_symlink(): linked.unlink()
            elif linked.is_junction(): linked.rmdir()

    def test_original_sources_are_byte_preserved(self):
        for path,data in self.originals.items():
            self.assertEqual(path.read_bytes(),data,str(path))

    def test_identity_transform_metadata_and_v0_v1_boxes_are_valid(self):
        self.assertEqual(self.packager._input_metadata(input_metadata().decode())["width"],1920)
        self.assertEqual(self.packager._input_metadata(text_rotation("-0.00").decode())["width"],1920)
        plain=probe_data()
        plain["streams"][0]["tags"]={"rotate":"0"}
        self.assertEqual(self.packager._probe_json(json.dumps(plain))["width"],1920)
        plain["streams"][0]["side_data_list"]=[{"side_data_type":"Display Matrix","rotation":0,
                                                   "displaymatrix":matrix_text(IDENTITY_MATRIX)}]
        self.assertEqual(self.packager._probe_json(json.dumps(plain))["width"],1920)
        for version in (0,1):
            with self.subTest(version=version):
                path=self.root/f"identity-v{version}.mp4"
                path.write_bytes(fake_mp4(movie_version=version,track_version=version))
                self.assertEqual(self.packager._mp4(path)["width"],1920)

    def test_text_and_probe_rotation_or_unknown_transform_is_rejected(self):
        for value in ("-180.00","90","NaN","Infinity","unknown"):
            with self.subTest(text=value):
                with self.assertRaises(self.packager.Invalid):
                    self.packager._input_metadata(text_rotation(value).decode())
                NEGATIVE_CASES.add("input-display-rotation-"+value)
        for label,value in (("tag-180",{"tags":{"rotate":"-180"}}),
                            ("tag-malformed",{"tags":{"rotate":"unknown"}}),
                            ("side-180",{"side_data_list":[{"side_data_type":"Display Matrix","rotation":-180}]}),
                            ("side-missing-matrix",{"side_data_list":[{"side_data_type":"Display Matrix","rotation":0}]}),
                            ("side-malformed",{"side_data_list":[{"side_data_type":"Display Matrix","rotation":0,"displaymatrix":"unknown"}]}),
                            ("side-hidden-translation",{"side_data_list":[{"side_data_type":"Display Matrix","rotation":0,
                                "displaymatrix":matrix_text((65536,0,0,0,65536,0,65536,0,1073741824))}]})):
            with self.subTest(probe=label):
                changed=probe_data(); changed["streams"][0].update(value)
                with self.assertRaises(self.packager.Invalid): self.packager._probe_json(json.dumps(changed))
                NEGATIVE_CASES.add("probe-transform-"+label)

    def test_movie_and_track_matrix_unknown_malformed_and_nonidentity_rejected(self):
        matrices={"rotate180":(-65536,0,0,0,-65536,0,0,0,1073741824),
                  "rotate90":(0,65536,0,-65536,0,0,0,0,1073741824),
                  "reflect":(-65536,0,0,0,65536,0,0,0,1073741824),
                  "translate":(65536,0,0,0,65536,0,65536,0,1073741824),
                  "scale":(32768,0,0,0,65536,0,0,0,1073741824),
                  "perspective":(65536,0,1,0,65536,0,0,0,1073741824),"zero":(0,)*9}
        cases=[(part+"-"+name,{part+"_matrix":matrix}) for part in ("movie","track") for name,matrix in matrices.items()]
        cases += [("missing-tkhd",{"omit_tkhd":True}),("short-tkhd",{"track_truncate":60}),
                  ("short-mvhd",{"movie_truncate":60}),("unknown-tkhd-version",{"track_version":2}),
                  ("unknown-mvhd-version",{"movie_version":2})]
        for name,options in cases:
            with self.subTest(name=name):
                path=self.root/(name+".mp4"); path.write_bytes(fake_mp4(**options))
                with self.assertRaises(self.packager.Invalid): self.packager._mp4(path)
                NEGATIVE_CASES.add("mp4-transform-"+name)

    def test_rejects_nonidentity_track_matrix(self):
        self.processes.video=fake_mp4(track_matrix=(-65536,0,0,0,-65536,0,0,0,1073741824))
        self.rejected("package-rotated-track-matrix")

    def test_sample_description_rejects_crop_unknown_and_nonsquare_pixels(self):
        path=self.root/"sample-description.mp4"
        path.write_bytes(fake_mp4(sample_children=((b"pasp",struct.pack(">II",1,1)),)))
        self.assertEqual(self.packager._mp4(path)["width"],1920)
        for label,children in (("nonsquare",((b"pasp",struct.pack(">II",2,1)),)),
                               ("zero",((b"pasp",bytes(8)),)),("short",((b"pasp",bytes(4)),)),
                               ("crop",((b"clap",bytes(32)),)),("unknown",((b"zzzz",bytes(8)),)),
                               ("duplicate-pasp",((b"pasp",struct.pack(">II",1,1)),)*2)):
            with self.subTest(label=label):
                path.write_bytes(fake_mp4(sample_children=children))
                with self.assertRaises(self.packager.Invalid): self.packager._mp4(path)
                NEGATIVE_CASES.add("mp4-sample-transform-"+label)

    def test_disabled_transform_and_consumer_guards_are_killed(self):
        source=self.originals[PACKAGER]
        cases=(("matrix", "MP4 display matrix must be identity: ","test_rejects_nonidentity_track_matrix",
                "package_full_animation"),
               ("consumer-inventory","Candidate directory is incomplete, failed or contains unexpected files.",
                "test_consumer_rejects_success_report_with_failure_marker","validate_candidate"))
        for label,detail,test_name,entry_point in cases:
            with self.subTest(mutant=label):
                tree,changed=ast.parse(source),0
                for node in ast.walk(tree):
                    if not (isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=="require"
                            and len(node.args)>1): continue
                    text=node.args[1]
                    match=(isinstance(text,ast.Constant) and text.value==detail or
                           isinstance(text,ast.BinOp) and isinstance(text.left,ast.Constant) and text.left.value==detail)
                    if (label=="consumer-inventory" and isinstance(text,ast.Constant)
                            and text.value=="Final output inventory changed before publication."):
                        match=True
                    if match: node.args[0]=ast.Constant(True); changed+=1
                self.assertEqual(changed,2 if label=="consumer-inventory" else 1,
                                 "Disable exactly the selected real guards, not test expectations")
                mutant=types.ModuleType("_m6_artificial_disabled_"+label.replace("-","_")); mutant.__file__=str(PACKAGER)
                exec(compile(ast.fix_missing_locations(tree),"<in-memory-disabled-"+label+">","exec"),mutant.__dict__)
                result=unittest.TestResult()
                with mock.patch.object(self.packager,entry_point,getattr(mutant,entry_point)):
                    FullAnimationMediaTests(test_name).run(result)
                self.assertEqual(result.testsRun,1)
                self.assertEqual(len(result.errors),0,result.errors)
                self.assertEqual(len(result.failures),1,"Independent negative must kill mutant: "+label)
                self.assertIn("True is not False",result.failures[0][1])
                MUTATIONS.append({"name":"disable-"+label+"-guard-in-memory","killed":True,"negativeTest":test_name,
                    "guardsChanged":changed,"testsRun":1,"failures":1,"errors":0,
                    "actualAssertionFailure":result.failures[0][1],"sourceFilesChanged":False})
        self.assertEqual(PACKAGER.read_bytes(),source)

    def test_finalcheck_failure_with_cleanup_permission_fault_cannot_publish_success(self):
        original_check=self.packager._assert_inputs
        original_unlink=Path.unlink
        triggered=False
        unlink_attempts=[]
        def fail_final(*args,**kwargs):
            nonlocal triggered
            result=original_check(*args,**kwargs)
            if (self.output/"candidate-report.staged.json").exists():
                triggered=True
                raise self.packager.Invalid("TEST_FINAL_CHECK","ARTIFICIAL final input check failure")
            return result
        def deny_marker_cleanup(path,*args,**kwargs):
            if path.parent==self.output and path.name in ("candidate-report.json","sorter-demo.tracks.descriptor.json","candidate-report.staged.json"):
                unlink_attempts.append(path.name)
                raise PermissionError("ARTIFICIAL permission denial; no real Windows lock or policy change")
            return original_unlink(path,*args,**kwargs)
        with mock.patch.object(self.packager,"_assert_inputs",fail_final),mock.patch.object(Path,"unlink",deny_marker_cleanup):
            self.rejected("finalcheck-plus-cleanup-permission-fault")
        self.assertTrue(triggered,"The fault must reach the final check after report staging")
        consumer=self.packager.validate_candidate(self.output)
        self.assertIs(consumer["valid"],False)
        self.assertFalse((self.output/"candidate-report.json").exists())
        COMPOUND_OBSERVATIONS.append({"finalCheckFaultReached":triggered,"cleanupPermissionFaultConfigured":True,
            "actualUnlinkAttempts":unlink_attempts,"publishedSuccessReportExists":False,"consumerValid":False,
            "notice":"No actual OS file lock; zero unlink attempts means failure rejection does not depend on deletion."})

    def test_report_publish_failure_cannot_be_accepted(self):
        with mock.patch.object(self.packager,"_publish_report",side_effect=PermissionError("ARTIFICIAL publish denial")):
            self.rejected("atomic-report-publish-denied")
        self.assertFalse((self.output/"candidate-report.json").exists())

    def test_consumer_rejects_success_report_with_failure_marker(self):
        result=self.run_package()
        self.assertIs(result["valid"],True,result)
        write_json(self.output/"failure.json",{"valid":False,"status":"FAIL","note":"ARTIFICIAL stale-success conflict"})
        consumed=self.packager.validate_candidate(self.output)
        self.assertIs(consumed["valid"],False,consumed)
        NEGATIVE_CASES.add("consumer-success-report-plus-failure")

    def test_consumer_requires_complete_current_four_file_bundle(self):
        result=self.run_package()
        self.assertIs(result["valid"],True,result)
        original={p.name:p.read_bytes() for p in self.output.iterdir()}
        report_only=self.root/"report-only"; report_only.mkdir()
        (report_only/"candidate-report.json").write_bytes(original["candidate-report.json"])
        self.assertIs(self.packager.validate_candidate(report_only)["valid"],False)
        NEGATIVE_CASES.add("consumer-report-only")
        for name in ("sorter-demo.mp4","sorter-demo.tracks.json","sorter-demo.tracks.descriptor.json","candidate-report.json"):
            with self.subTest(tampered=name):
                path=self.output/name; path.write_bytes(original[name]+b"TAMPER")
                self.assertIs(self.packager.validate_candidate(self.output)["valid"],False)
                NEGATIVE_CASES.add("consumer-tampered-"+name)
                path.write_bytes(original[name])
        for name in ("candidate-report.staged.json","sorter-demo.partial.mp4","unknown.txt"):
            with self.subTest(extra=name):
                path=self.output/name; path.write_bytes(b"ARTIFICIAL INCOMPLETE STATE")
                self.assertIs(self.packager.validate_candidate(self.output)["valid"],False)
                NEGATIVE_CASES.add("consumer-extra-"+name)
                path.unlink()
        changed=json.loads(original["sorter-demo.tracks.descriptor.json"]); changed["videoSha256"]="0"*64
        write_json(self.output/"sorter-demo.tracks.descriptor.json",changed)
        report=json.loads(original["candidate-report.json"])
        report["assets"]["tracksDescriptor"]=digest(self.output/"sorter-demo.tracks.descriptor.json")
        report["tracksDescriptor"]=changed
        write_json(self.output/"candidate-report.json",report)
        self.assertIs(self.packager.validate_candidate(self.output)["valid"],False)
        NEGATIVE_CASES.add("consumer-tracks-video-binding")


if __name__=="__main__":
    unittest.main()
