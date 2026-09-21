"""Read-only PCM comparison of approved v1/v2 WAVs; stdlib, no API/network.

python scripts/media_pc2/measure_audio.py --v1-dir <preserved-v1-directory>
Only the JSON/Markdown reports under reports/pc2 are written. Audio, fixture,
manifest and recorded STT remain untouched. LUFS is not estimated from RMS.
"""
from __future__ import annotations

import argparse
from array import array
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import shutil
import sys
import wave

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "reports/pc2"
SOURCE_REPORT = "reports/audio-quality.md"
# Generation metadata intervals transcribed from the report's turn table.
# These are NOT STT timestamps and are never supplied to a model.
SOURCE_TURNS = {
    "CASE-0001": [(0, 5.10), (5.45, 11.90), (12.25, 16.35),
                  (16.70, 23), (23.35, 30.20), (30.55, 35.80),
                  (36.15, 44), (44.35, 46.80)],
    "CASE-0002": [(0, 4.30), (4.65, 12.20), (12.55, 17.20),
                  (17.55, 23.10), (23.45, 29.60), (29.95, 36.35),
                  (36.70, 44.05), (44.40, 49.20)],
}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def dbfs(amplitude: float) -> float | None:
    """None represents negative infinity for a digital-silence signal."""
    return 20 * math.log10(amplitude) if amplitude > 0 else None


def load_pcm(path: Path) -> tuple[dict, array]:
    with wave.open(str(path), "rb") as reader:
        rate, channels, width, frames = (reader.getframerate(), reader.getnchannels(),
                                        reader.getsampwidth(), reader.getnframes())
        if width != 2 or reader.getcomptype() != "NONE" or frames <= 0:
            raise ValueError(f"Expected nonempty uncompressed PCM16 WAV: {path.name}")
        raw = reader.readframes(frames)
    if len(raw) != frames * channels * width:
        raise ValueError(f"Truncated PCM payload: {path.name}")
    samples = array("h", raw)
    if sys.byteorder != "little":
        samples.byteswap()
    return {"sample_rate_hz": rate, "channels": channels, "bits_per_sample": 16,
            "frames": frames, "duration_seconds": frames / rate}, samples


def metrics(shape: dict, samples: array, start: float = 0,
            end: float | None = None) -> dict:
    rate, channels = shape["sample_rate_hz"], shape["channels"]
    end = shape["duration_seconds"] if end is None else end
    if (not math.isfinite(start) or not math.isfinite(end)
            or not 0 <= start < end <= shape["duration_seconds"]):
        raise ValueError("Segment must be finite, ordered and within the WAV duration")
    first, last = round(start * rate), round(end * rate)
    if first >= last:
        raise ValueError("Segment contains no PCM frames")
    selected = samples[first * channels:last * channels]
    count = len(selected)
    if count != (last - first) * channels:
        raise ValueError("PCM sample count differs from the declared shape")
    peak = max(abs(value) for value in selected)
    rms = math.sqrt(sum(value * value for value in selected) / count)
    window_samples = max(1, round(rate * .02)) * channels
    windows = count // window_samples
    quiet = 0
    for offset in range(0, windows * window_samples, window_samples):
        block = selected[offset:offset + window_samples]
        quiet += sum(value * value for value in block) / window_samples / 32768**2 < 1e-5
    zeros = selected.count(0)
    rails = sum(value in (-32768, 32767) for value in selected)
    return {
        "start_seconds": first / rate, "end_seconds": last / rate,
        "frames": last - first, "sample_count": count,
        "duration_seconds": (last - first) / rate,
        "sample_peak_dbfs": dbfs(peak / 32768),
        "rms_dbfs": dbfs(rms / 32768), "digital_rail_samples": rails,
        "digital_rail_percent": rails * 100 / count,
        "above_minus_1_dbfs_samples": sum(abs(value) / 32768 >= 10**(-1 / 20) for value in selected),
        "exact_zero_samples": zeros, "exact_zero_percent": zeros * 100 / count,
        "quiet_20ms_windows": quiet, "complete_20ms_windows": windows,
        "quiet_20ms_percent": quiet * 100 / windows if windows else None,
        "excluded_tail_frames": (count % window_samples) // channels,
    }


def relative(path: Path) -> str:
    path = path.resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def check_entry(name: str, passed: bool, detail: str) -> dict:
    return {"id": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def compare(v1_dir: Path) -> dict:
    manifest_path = ROOT / "data/demo-media-manifest.json"
    fixture_path = ROOT / "data/fixtures/cases.json"
    stt_path = ROOT / "reports/e2e/normalized-voice-live.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    stt = json.loads(stt_path.read_text(encoding="utf-8"))
    if stt.get("caseId") != "CASE-0002":
        raise ValueError("Expected the separately recorded CASE-0002 live response")
    tool_discovery = {"ffmpeg_on_path": shutil.which("ffmpeg"),
                      "ffprobe_on_path": shutil.which("ffprobe"),
                      "imageio_ffmpeg_module_found": importlib.util.find_spec("imageio_ffmpeg") is not None,
                      "lufs_measurement_executed": False, "tools_downloaded": False}
    cases_by_id = {item["id"]: item for item in fixture["cases"]}
    assets = {item["name"]: item for item in manifest["assets"]}
    protected = [manifest_path, fixture_path, stt_path, ROOT / SOURCE_REPORT]
    protected += [directory / f"{case_id}.wav" for case_id in SOURCE_TURNS
                  for directory in (v1_dir, ROOT / "apps/web/public/demo")]
    before_hashes = {relative(path): digest(path) for path in protected}
    results, checks = [], []
    for case_id, windows in SOURCE_TURNS.items():
        asset = assets[f"{case_id}.wav"]
        case = cases_by_id[case_id]
        versions, pcm = {}, {}
        for version, directory, size_key, hash_key in (
                ("v1", v1_dir, "sourceBytes", "sourceSha256"),
                ("v2", ROOT / "apps/web/public/demo", "bytes", "sha256")):
            path = directory / asset["name"]
            actual_hash = before_hashes[relative(path)]
            if actual_hash != asset[hash_key] or path.stat().st_size != asset[size_key]:
                raise ValueError(f"{case_id} {version}: approved bytes/SHA256 mismatch; not measured as an approved version")
            shape, samples = load_pcm(path)
            versions[version] = {"path": relative(path), "bytes": path.stat().st_size,
                                 "sha256": actual_hash, "shape": shape,
                                 "pcm": metrics(shape, samples)}
            pcm[version] = (shape, samples)
        shape_equal = versions["v1"]["shape"] == versions["v2"]["shape"]
        checks.append(check_entry(case_id + "-format-and-frames-preserved", shape_equal,
                                  "Exact PCM frame count, rate, channels, bit depth and duration"))
        if not shape_equal:
            raise ValueError(f"{case_id}: frame/format mismatch; source windows cannot be reused")
        turns = []
        if len(case["transcript"]) != len(windows):
            raise ValueError("Generation script turn count differs from the cited timing table")
        for index, ((start, end), turn) in enumerate(zip(windows, case["transcript"]), 1):
            measured = {version: metrics(*pcm[version], start, end) for version in pcm}
            turns.append({"turn": index, "speaker": turn["speaker"],
                          "generation_script_text": turn["text"],
                          "timing_source": SOURCE_REPORT + " generation-turn table (pc1 metadata citation)",
                          "not_stt_timestamps": True, "start_seconds": start, "end_seconds": end,
                          "v1": measured["v1"], "v2": measured["v2"],
                          "rms_change_db": measured["v2"]["rms_dbfs"] - measured["v1"]["rms_dbfs"]})
        checks.append(check_entry(case_id + "-v2-zero-digital-clipping",
                                  versions["v2"]["pcm"]["digital_rail_samples"] == 0,
                                  "PCM16 rail reach count only; not a listening verdict"))
        results.append({"case_id": case_id, "versions": versions, "generation_turns": turns,
                        "lufs_true_peak": {"measurement_on_this_pc": "NOT_MEASURED",
                            "reason": "This standard-library PCM tool does not compute LUFS/true peak; inspect tool_discovery and cited pc1 measurements",
                            "v1_pc1_report": {"source": SOURCE_REPORT,
                                "integrated_lufs": -22.0 if case_id == "CASE-0001" else -22.1,
                                "true_peak_dbtp": -3.6 if case_id == "CASE-0001" else -3.3},
                            "v2_pc1_manifest": {"source": "data/demo-media-manifest.json",
                                "integrated_lufs": asset["processing"]["integratedLufs"],
                                "true_peak_dbtp": asset["processing"]["truePeakDbtp"]}}})
        if stt["caseId"] == case_id:
            if stt["audioSha256"] != versions["v2"]["sha256"] or stt["result"]["mode"] != "demo-live":
                raise ValueError("Recorded live transcript is not bound to the measured v2 WAV")
            stt_segments = [{"index": index, "speaker": segment["speaker"],
                             "text": segment["text"], "start": segment["start"], "end": segment["end"],
                             "v2_pcm": metrics(*pcm["v2"], segment["start"], segment["end"])}
                            for index, segment in enumerate(stt["result"]["transcript"], 1)]
    # Hash again after all reads so this report cannot claim integrity from stale hashes.
    unchanged = all(digest(path) == before_hashes[relative(path)] for path in protected)
    checks.append(check_entry("protected-inputs-unchanged", unchanged,
                              f"{len(protected)} audio/source/report inputs hashed before and after"))
    fields = stt["result"]["analysis"]["fields"]
    stt_check = (fields["quantity"] == 1 and fields["unit"] == "BOX" and fields["storeId"] is None)
    checks.append(check_entry("recorded-single-live-response-semantics", stt_check,
                              "Existing CASE-0002 response: received 1 BOX and unidentified store; no new STT request"))
    return {"schema_version": 1, "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "measured_hostname": platform.node(), "python": platform.python_version(),
            "network_calls": 0, "paid_api_calls": 0, "audio_written": False,
            "tool_discovery": tool_discovery,
            "input_hashes": before_hashes, "cases": results,
            "recorded_live_response": {"source": relative(stt_path), "started_at": stt["startedAt"],
                "case_id": stt["caseId"], "audio_sha256": stt["audioSha256"],
                "request_id": stt["result"]["requestId"], "segments": stt_segments,
                "analysis_fields": fields, "replay_cases_are_not_live_stt": ["CASE-0001"],
                "new_requests_in_this_measurement": 0},
            "checks": checks, "passed": sum(row["status"] == "PASS" for row in checks),
            "total_checks": len(checks), "all_technical_checks_passed": all(row["status"] == "PASS" for row in checks),
            "human_listening": "NOT_PERFORMED", "browser_playback": "NOT_PERFORMED_BY_THIS_TOOL",
            "limits": ["RMS and sample peak are PCM measurements, not LUFS or true peak.",
                       "Quiet-window and zero-sample ratios are not missing-speech or STT error rates.",
                       "Source generation intervals are cited pc1 metadata, not newly inferred STT timestamps.",
                       "One recorded live CASE-0002 response is not an accuracy denominator of 20 or a before/after STT experiment.",
                       "OS output, human word recognition, speaker distinction by listening and overall clarity remain unverified."]}


def number(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "무음(-∞)"


def markdown(report: dict, v1_dir: Path) -> str:
    lines = ["# N02 pc2 음성 실측", "", f"실측 UTC: {report['measured_at_utc']} / hostname {report['measured_hostname']} / Python {report['python']}.",
             "", "승인 v1·v2 WAV를 읽어 비교했다. 음원·원본·manifest·전사 기록은 변경하지 않았다. 유료/API·네트워크 호출 0회.",
             "**수치 측정 통과는 사람 청취 명료도 합격이 아니다. 사람 청취·OS 출력은 미검증이다.**", "",
             "## 재현", "", "저장소 루트에서 실행한다. v1 경로는 실제 보존 백업으로 지정한다.", "", "```powershell",
             f'python scripts/media_pc2/measure_audio.py --v1-dir "{relative(v1_dir)}"',
             "python -m unittest discover -s scripts/media_pc2 -p 'test_*.py' -v", "```", "",
             "도구는 Python 표준 라이브러리만 사용한다. WAV가 manifest의 승인 크기·SHA와 다르면 중단한다. 입력은 측정 전후 SHA를 대조한다.", "",
             "## 파일 전체 PCM 측정", "", "| 사례 | 버전 | 길이(s) | 프레임 | 형식 | sample peak(dBFS) | RMS(dBFS) | rail/샘플 수 | 0 샘플(%) | 조용한20ms(%) |", "|---|---|---:|---:|---|---:|---:|---|---:|---:|"]
    for case in report["cases"]:
        for version, entry in case["versions"].items():
            shape, pcm = entry["shape"], entry["pcm"]
            lines.append(f"| {case['case_id']} | {version} | {shape['duration_seconds']:.3f} | {shape['frames']} | {shape['sample_rate_hz']}Hz/{shape['channels']}ch/{shape['bits_per_sample']}bit | {number(pcm['sample_peak_dbfs'])} | {number(pcm['rms_dbfs'])} | {pcm['digital_rail_samples']}/{pcm['sample_count']} | {pcm['exact_zero_percent']:.2f} | {pcm['quiet_20ms_percent']:.2f} |")
    lines += ["", "rail은 PCM16의 -32768 또는 32767 도달 샘플이다. 20ms 창의 RMS가 -50dBFS 미만이면 조용한 창으로 센다. 마지막 불완전 창은 분모에서 제외한다. 무음 비율은 발화 누락률이 아니다. RMS는 전체 파일·해당 구간의 휴지를 포함한다.",
              "", "## 생성 발화 구간 비교", "", "시각은 pc1 `reports/audio-quality.md`의 생성 메타데이터 표 인용이다. pc2에는 `.local/tts-segments`가 없어 원본 metadata를 재검증하지 않았다. 두 WAV의 프레임/형식이 같음을 실측한 뒤 동일 구간을 비교했다. 이 시각은 실제 STT의 자막 시각이 아니다.", "",
              "| 사례/발화 | 화자 | 생성 구간(s) | v1 RMS | v2 RMS | 차이(dB) |", "|---|---|---|---:|---:|---:|"]
    for case in report["cases"]:
        for turn in case["generation_turns"]:
            lines.append(f"| {case['case_id']}/{turn['turn']} | {turn['speaker']} | {turn['start_seconds']:.2f}–{turn['end_seconds']:.2f} | {number(turn['v1']['rms_dbfs'])} | {number(turn['v2']['rms_dbfs'])} | {turn['rms_change_db']:+.2f} |")
    live = report["recorded_live_response"]
    correction = next(item for item in live["segments"] if "아니요" in item["text"] and "박스" in item["text"])
    lines += ["", "## 실제 STT 기록과 핵심 정정", "",
              f"기존 {live['source']}의 CASE-0002 1회 live 응답을 읽었다. 입력 SHA가 이번 v2 SHA와 일치하며 {len(live['segments'])}개 STT 구간 모두 WAV 범위 안에 있다. 새 전사 호출은 0회다.",
              f"- 정정 자막은 {correction['start']:.2f}–{correction['end']:.2f}초: `{correction['text'].strip()}`. 이 구간의 v2 RMS는 {number(correction['v2_pcm']['rms_dbfs'])} dBFS다.",
              "- 생성 발화4의 17.55–23.10초와 위 STT 구간은 출처·분절이 다르다. 임의로 일치시키거나 생성 대본을 실제 전사로 대체하지 않는다.",
              "- 이 기록의 수령은 1 BOX, 점포ID는 null이다. 주문18 EA를 수령량으로 바꾸거나 가상 새봄점으로 자동 확정하지 않는다.",
              "- CASE-0001에는 이번에 읽은 실제 live 응답이 없다. 대본/replay를 실제 STT 실적으로 세지 않는다.",
              "- 서비스명·점포명·상품명·정정/오출고 용어의 불일치가 남아 있다. v1/v2의 전사 품질 개선률이나 전체 문자 오류율을 계산하지 않았다.",
              "", "## LUFS·true peak: 메인 측정 인용", "",
              "아래 값은 새 실측이 아니라 SHA로 연결된 메인 보고·manifest 인용이며 RMS로 추정한 값이 아니다. FFmpeg를 실행하거나 설치·다운로드하지 않았다. 이번 실행의 도구 탐색 결과: " + json.dumps(report["tool_discovery"], ensure_ascii=False) + ".", "",
              "| 사례 | v1 LUFS / true peak | v2 LUFS / true peak |", "|---|---|---|"]
    for case in report["cases"]:
        refs = case["lufs_true_peak"]
        a, b = refs["v1_pc1_report"], refs["v2_pc1_manifest"]
        lines.append(f"| {case['case_id']} | {a['integrated_lufs']} / {a['true_peak_dbtp']} dBTP | {b['integrated_lufs']} / {b['true_peak_dbtp']} dBTP |")
    lines += ["", "## 기술 검사와 미검증", "",
              f"실파일 비교 검사 {report['passed']}/{report['total_checks']} PASS. 승인 v1/v2 4개 파일의 SHA·크기 확인 뒤 측정했다. 검사는 두 사례의 형식/프레임 보존, v2 디지털 rail 0, 모든 입력의 전후 불변, 기존 live 1건의 수령1BOX·점포미확인을 확인한다.",
              "", "사람 청취/OS 출력/브라우저 배속·볼륨·키보드 동작은 이 도구의 검증 범위 밖이다. 단위 구간이 커졌다는 수치만으로 두 화자·고유명사·업무 용어를 알아듣는다고 판정하지 않는다. 별도 UI 검증과 사람 청취 결과가 필요하다.", "",
              "기계 판독 결과와 전체 SHA·분모·STT 구간별 PCM 측정: `reports/pc2/audio-quality.json`. 재생성 후보·청취 계획은 `planning/media/voice-scenarios.md`. 이 측정은 음성 편집이나 새로운 TTS/STT 실행이 아니다.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1-dir", required=True, type=Path)
    args = parser.parse_args()
    report = compare(args.v1_dir.resolve())
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "audio-quality.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (REPORT_DIR / "audio-quality.md").write_text(markdown(report, args.v1_dir.resolve()), encoding="utf-8")
    print(json.dumps({"report": "reports/pc2/audio-quality.json", "checks": report["total_checks"],
                      "passed": report["passed"], "paid_api_calls": 0,
                      "human_listening": report["human_listening"]}, ensure_ascii=False))
    return 0 if report["all_technical_checks_passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, wave.Error, KeyError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
