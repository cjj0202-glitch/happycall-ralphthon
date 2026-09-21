"""Evidence-gated, single-writer task board. Standard library only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATES = {"TODO", "DOING", "REVIEW", "DONE", "BLOCKED", "DEFERRED"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def local_file(root, value):
    path = (root / value).resolve()
    if Path(value).is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError("파일은 저장소 내부 상대경로여야 합니다")
    return path


def spec_hash(task):
    spec = {k: task[k] for k in ("id", "depends_on", "outputs", "checks")}
    return hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate(plan):
    tasks = plan["tasks"]
    ids = [t["id"] for t in tasks]
    if not tasks or len(set(ids)) != len(ids):
        raise ValueError("작업 ID는 비어 있거나 중복될 수 없습니다")
    by_id = {t["id"]: t for t in tasks}
    for task in tasks:
        if task["state"] not in STATES or task["owner"] not in {"pc1", "pc2", "pc3", "pc4"}:
            raise ValueError(f"잘못된 상태/담당: {task['id']}")
        if not task["checks"] or not task["outputs"]:
            raise ValueError(f"완료 기준/산출물이 없습니다: {task['id']}")
        if any(d not in by_id for d in task["depends_on"]):
            raise ValueError(f"없는 선행 작업: {task['id']}")
        if task["state"] in {"DOING", "REVIEW", "DONE"} and any(by_id[d]["state"] != "DONE" for d in task["depends_on"]):
            raise ValueError(f"미완료 선행 작업: {task['id']}")
    visiting, visited = set(), set()

    def walk(key):
        if key in visiting:
            raise ValueError(f"순환 의존성: {key}")
        if key in visited:
            return
        visiting.add(key)
        for dependency in by_id[key]["depends_on"]:
            walk(dependency)
        visiting.remove(key)
        visited.add(key)

    for key in ids:
        walk(key)
    for owner in {t["owner"] for t in tasks}:
        active = [t for t in tasks if t["owner"] == owner and t["state"] in {"DOING", "REVIEW"}]
        if len(active) > 1:
            raise ValueError(f"{owner}: 진행/검증 대기는 합쳐서 하나만 허용됩니다")


def verify_evidence(root, task, filename):
    path = local_file(root, filename)
    evidence = read(path)
    if evidence.get("task_id") != task["id"] or evidence.get("spec_hash") != spec_hash(task):
        raise ValueError("증거의 작업 ID 또는 완료 기준 버전이 다릅니다")
    if not evidence.get("measured_at") or not evidence.get("observer"):
        raise ValueError("측정 시각과 관측자가 필요합니다")
    checks = evidence.get("checks", {})
    if set(checks) != set(task["checks"]):
        raise ValueError("완료 기준이 누락되거나 추가되었습니다")
    for key, expected in task["checks"].items():
        item = checks[key]
        if item.get("passed") is not True or item.get("expected") != expected or not str(item.get("observed", "")).strip():
            raise ValueError(f"미통과/기대값 불일치/관측 누락: {key}")
    artifacts = evidence.get("artifacts", [])
    if not set(task["outputs"]).issubset(artifacts):
        raise ValueError("필수 산출물이 증거에 없습니다")
    hashes = {}
    for name in [filename, *artifacts]:
        artifact = local_file(root, name)
        if not artifact.is_file() or artifact.stat().st_size == 0:
            raise ValueError(f"산출물이 없거나 비었습니다: {name}")
        hashes[name] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    return hashes


def main_pc(root):
    slots = read(root / "channel/pcs.json")["slots"]
    if platform.node() not in slots["pc1"]["hostname"] or slots["pc1"]["role"] != "main":
        raise ValueError("중앙 작업표 변경은 등록된 pc1만 합니다. 워커는 증거 파일로 제출합니다")


def transition(plan, task_id, action, root, evidence=None, reason=None):
    validate(plan)
    task = next((t for t in plan["tasks"] if t["id"] == task_id), None)
    if task is None:
        raise ValueError("작업 ID가 없습니다")
    before = task["state"]
    target = {"start": "DOING", "review": "REVIEW", "accept": "DONE", "block": "BLOCKED", "resume": "TODO", "reject": "TODO"}[action]
    allowed = {"start": {"TODO"}, "review": {"DOING"}, "accept": {"REVIEW"}, "block": {"DOING", "REVIEW"}, "resume": {"BLOCKED"}, "reject": {"REVIEW"}}
    if before not in allowed[action]:
        raise ValueError(f"{before}에서 {action}할 수 없습니다")
    if action in {"block", "resume", "reject"} and not reason:
        raise ValueError("상태 변경 사유가 필요합니다")
    if action == "start":
        slot = read(root / "channel/pcs.json")["slots"][task["owner"]]
        if not slot.get("hostname") or not slot.get("github") or slot.get("role") == "미정":
            raise ValueError("담당 PC의 hostname·GitHub·역할 등록이 필요합니다")
    hashes = verify_evidence(root, task, evidence) if action == "accept" and evidence else None
    if action == "accept" and hashes is None:
        raise ValueError("완료에는 --evidence 파일이 필요합니다")
    # Validate the proposed state before committing any mutation.
    proposed = json.loads(json.dumps(plan))
    changed = next(t for t in proposed["tasks"] if t["id"] == task_id)
    changed["state"] = target
    if hashes is not None:
        changed["evidence"] = evidence
        changed["artifact_hashes"] = hashes
        changed["reviewer"] = "pc1"
    changed.setdefault("history", []).append({"at": stamp(), "from": before, "to": target, "reason": reason or action})
    validate(proposed)
    return proposed


def markdown(plan):
    done = sum(t["state"] == "DONE" for t in plan["tasks"])
    lines = ["# OneFlow 작업표", "", "> 정본: ops/tasks.json. 이 파일은 `python ops/tasks.py render`로 생성합니다.",
             "> 체크는 pc1의 증거 검증 뒤에만 붙습니다. 담당 슬롯은 역할 제안이며 PC 등록 전에는 배정되지 않습니다.",
             "", f"전체 {len(plan['tasks'])}개 중 {done}개 완료. 준비 작업을 포함한 수치이며 제품 완성률이 아닙니다.", ""]
    phase = None
    for task in plan["tasks"]:
        if phase != task["phase"]:
            phase = task["phase"]
            lines += [f"## {phase}", ""]
        lines += [f"- [{'x' if task['state'] == 'DONE' else ' '}] **{task['id']} {task['title']}** — {task['owner']} · {task['state']} · {task['minutes']}분",
                  f"  선행: {', '.join(task['depends_on']) or '없음'} / 산출물: {', '.join(task['outputs'])}"]
        for key, expected in task["checks"].items():
            lines.append(f"  - {key}: {expected}")
        if task.get("evidence"):
            lines.append(f"  - 검증 기록: [{task['evidence']}]({task['evidence']})")
        lines.append("")
    return "\n".join(lines)


def atomic(path, content):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(content, encoding="utf-8")
    os.replace(temp, path)


@contextmanager
def lock(root):
    path = root / "ops/.tasks.lock"
    with path.open("x", encoding="utf-8") as stream:
        stream.write(f"pid={os.getpid()} at={stamp()}")
    try:
        yield
    finally:
        path.unlink()


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["status", "next", "show", "template", "check", "render", "start", "review", "accept", "block", "resume", "reject"])
    parser.add_argument("task", nargs="?")
    parser.add_argument("--pc", choices=["pc1", "pc2", "pc3", "pc4"])
    parser.add_argument("--evidence")
    parser.add_argument("--reason")
    args = parser.parse_args()
    plan = read(ROOT / "ops/tasks.json")
    validate(plan)
    tasks = plan["tasks"]
    if args.command == "check":
        if (ROOT / "TODO.md").read_text(encoding="utf-8") != markdown(plan):
            raise ValueError("TODO.md가 정본과 다릅니다. render를 실행하세요")
        for task in tasks:
            if task["state"] == "DONE":
                hashes = verify_evidence(ROOT, task, task["evidence"])
                if hashes != task["artifact_hashes"]:
                    raise ValueError(f"완료 후 산출물이 변경되었습니다. 재검토 필요: {task['id']}")
        print(f"PASS: 작업 {len(tasks)}개, 의존성·WIP·TODO 일치·완료 증거 확인")
    elif args.command == "status":
        for state in sorted(STATES):
            print(f"{state}: {sum(t['state'] == state for t in tasks)}")
    elif args.command == "next":
        if not args.pc:
            raise ValueError("next에는 --pc가 필요합니다")
        selected = [t for t in tasks if t["owner"] == args.pc]
        active = [t for t in selected if t["state"] in {"DOING", "REVIEW"}]
        finished = {t["id"] for t in tasks if t["state"] == "DONE"}
        ready = [t for t in selected if t["state"] == "TODO" and set(t["depends_on"]).issubset(finished)]
        print(json.dumps((active or ready)[:1], ensure_ascii=False, indent=2))
    elif args.command in {"show", "template"}:
        task = next((t for t in tasks if t["id"] == args.task), None)
        if task is None:
            raise ValueError("작업 ID가 필요합니다")
        value = task if args.command == "show" else {
            "task_id": task["id"], "spec_hash": spec_hash(task), "measured_at": "", "observer": "",
            "checks": {key: {"expected": text, "observed": "", "passed": False} for key, text in task["checks"].items()},
            "artifacts": task["outputs"],
        }
        print(json.dumps(value, ensure_ascii=False, indent=2))
    else:
        main_pc(ROOT)
        with lock(ROOT):
            plan = read(ROOT / "ops/tasks.json")
            if args.command != "render":
                plan = transition(plan, args.task, args.command, ROOT, args.evidence, args.reason)
                atomic(ROOT / "ops/tasks.json", json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
            atomic(ROOT / "TODO.md", markdown(plan))
        print(f"OK: {args.command} {args.task or ''}")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    try:
        sys.exit(run())
    except (ValueError, OSError, KeyError, StopIteration) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
