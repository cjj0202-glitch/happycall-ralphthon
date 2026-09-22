"""Read existing personal AWS settings into ignored, private handoff files.

No AWS mutation, API generation, credential printing, or existing-file overwrite.
Run on the recovered main PC after configuring its existing personal AWS profile.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = "704995468470"
REGION = "ap-northeast-2"
FUNCTION = "happycall-oneflow-api"
DESTINATION = ROOT / ".local/main-pc-handoff-20260922"
ENV_KEYS = ("OPENAI_API_KEY", "OPENAI_DEMO_PURPOSE", "OPENAI_DEMO_BUDGET_USD", "OPENAI_DEMO_WARN_USD")


def aws_json(executable, profile, *arguments):
    result = subprocess.run([executable, *arguments, "--profile", profile, "--region", REGION,
                             "--output", "json", "--no-cli-pager"], capture_output=True)
    if result.returncode:
        raise ValueError("AWS_READ_FAILED_CHECK_EXISTING_PERSONAL_PROFILE")
    try:
        return json.loads(result.stdout)
    except (ValueError, UnicodeError):
        raise ValueError("AWS_RESPONSE_INVALID") from None


def render_private_files(environment, url):
    required = (*ENV_KEYS, "ONEFLOW_ACCESS_USER", "ONEFLOW_ACCESS_PASSWORD")
    if any(not isinstance(environment.get(key), str) or not environment[key]
           or any(char in environment[key] for char in "\r\n\x00") for key in required):
        raise ValueError("REQUIRED_SERVER_CONFIGURATION_MISSING")
    if not environment["OPENAI_API_KEY"].startswith("sk-"):
        raise ValueError("API_KEY_FORMAT_INVALID")
    if (environment["OPENAI_DEMO_PURPOSE"] != "demo-only"
            or environment["OPENAI_DEMO_BUDGET_USD"] != "30"
            or environment["OPENAI_DEMO_WARN_USD"] != "25"):
        raise ValueError("EXISTING_BUDGET_POLICY_CHANGED")
    private = ("# 복구 메인 PC 비공개 접속 인계\n\n"
               "사용자가 명시 요청한 API 키·로그인 정보입니다. 이 파일은 Git 제외이며 공유 이슈에 붙여 넣지 않습니다.\n\n"
               f"배포 주소: {url}\n\n"
               f"사용자 이름: {environment['ONEFLOW_ACCESS_USER']}\n\n"
               f"비밀번호: {environment['ONEFLOW_ACCESS_PASSWORD']}\n\n"
               f"OpenAI API 키: {environment['OPENAI_API_KEY']}\n\n"
               "키는 현재 개인 AWS Lambda에서 실제 사용하는 값을 가져왔습니다. 모델은 gpt-4.1-mini이며 전용 학습은 하지 않았습니다. "
               "공유 원장의 기존 보수 예약은 29.35/30달러였습니다. 실제 최신 잔액을 확인하고 원장을 초기화하지 마세요.\n\n"
               "함께 저장한 openai.env는 보관본이며 프로그램이 자동으로 읽지 않습니다. 다른 PC의 기존 환경 파일에 자동 덮어쓰지 않습니다.\n")
    return {"PRIVATE_ACCESS.md": private,
            "openai.env": "\n".join(key + "=" + environment[key] for key in ENV_KEYS) + "\n",
            "access.json": json.dumps({"username": environment["ONEFLOW_ACCESS_USER"],
                                        "password": environment["ONEFLOW_ACCESS_PASSWORD"]}, indent=2) + "\n"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="scmops-lab")
    args = parser.parse_args()
    try:
        targets = [DESTINATION / name for name in ("PRIVATE_ACCESS.md", "openai.env", "access.json")]
        if any(path.exists() for path in targets):
            raise ValueError("EXISTING_PRIVATE_FILES_PRESERVED_NO_OVERWRITE")
        for target in targets:
            check = subprocess.run(["git", "check-ignore", "--quiet", "--", str(target)], cwd=ROOT,
                                   capture_output=True)
            if check.returncode != 0:
                raise ValueError("PRIVATE_DESTINATION_NOT_GIT_IGNORED")
        executable = shutil.which("aws")
        if not executable and Path(r"C:\Program Files\Amazon\AWSCLIV2\aws.exe").is_file():
            executable = r"C:\Program Files\Amazon\AWSCLIV2\aws.exe"
        if not executable:
            raise ValueError("AWS_CLI_REQUIRED")
        identity = aws_json(executable, args.profile, "sts", "get-caller-identity")
        if identity.get("Account") != ACCOUNT:
            raise ValueError("WRONG_AWS_ACCOUNT")
        config = aws_json(executable, args.profile, "lambda", "get-function-configuration", "--function-name", FUNCTION)
        if config.get("FunctionArn") != f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{FUNCTION}":
            raise ValueError("WRONG_LAMBDA_FUNCTION")
        url = aws_json(executable, args.profile, "lambda", "get-function-url-config", "--function-name", FUNCTION)["FunctionUrl"]
        files = render_private_files(config.get("Environment", {}).get("Variables", {}), url)
        DESTINATION.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            with (DESTINATION / name).open("x", encoding="utf-8", newline="\n") as output:
                output.write(content)
        print(json.dumps({"status": "private_handoff_created", "account": ACCOUNT,
                          "files": [str(path.relative_to(ROOT)) for path in targets],
                          "awsMutation": False, "aiCalls": 0, "secretValuesPrinted": False}))
        return 0
    except (ValueError, OSError, KeyError) as error:
        # No raw AWS response, secret, submitted value, or SDK exception is emitted.
        code = str(error) if type(error) is ValueError else type(error).__name__
        print(json.dumps({"status": "not_completed", "code": code}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
