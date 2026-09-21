"""Synthetic-only controls; no original logs, credentials or network access."""
import base64
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import types
import unittest
from unittest.mock import patch
import zlib


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_submission_log.py"
SPEC = importlib.util.spec_from_file_location("submission_log_under_test", SCRIPT)
SUT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUT)


def synthetic_key():
    return "sk-" + "proj-" + "SYNTHETIC" * 5


def digest(value):
    return hashlib.sha256(value).hexdigest()


def synthetic_png():
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))
    image = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
             + chunk(b"IDAT", zlib.compress(b"\x00\x10\x20\x30")) + chunk(b"IEND", b""))
    return base64.b64encode(image).decode("ascii")


def transform(module, value, policy=frozenset()):
    counts, entries = module.Counter(), []
    result = module.transform(value, policy, 1, entries.append, counts)
    return result, entries, counts


class SubmissionLogTests(unittest.TestCase):
    def setUp(self):
        SUT.LOCAL_ROOT.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="submission-synthetic-", dir=SUT.LOCAL_ROOT)
        self.root = Path(self.temp.name)
        self.source = self.root / "fixed-synthetic.jsonl"
        self.output = self.root / "new-candidate"

    def tearDown(self):
        self.temp.cleanup()

    def write(self, events):
        self.source.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n", encoding="utf-8")

    def run_cli(self, extra=()):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = SUT.main(["--input", str(self.source), "--output-dir", str(self.output), *extra])
        return code, out.getvalue(), err.getvalue()

    def load_output(self):
        return [json.loads(line) for line in (self.output / SUT.CANDIDATE).read_text(encoding="utf-8").splitlines()]

    def test_positive_credentials_contacts_and_media(self):
        basic = base64.b64encode(b"synthetic-user:synthetic-password").decode()
        jwt = ".".join(base64.urlsafe_b64encode(x).decode().rstrip("=") for x in
                       (b'{"alg":"HS256"}', b'{"sub":"SYNTHETIC"}', b"synthetic-signature"))
        examples = {
            "OPENAI_KEY": synthetic_key(),
            "GITHUB_TOKEN": "ghp_" + "S" * 36,
            "AWS_ACCESS_KEY": "AKIA" + "S" * 16,
            "AWS_SECRET": "aws_secret_access_key=" + "S" * 40,
            "URL_CREDENTIAL": "https://synthetic:password@example.invalid/test",
            "BEARER_TOKEN": "Bearer " + "S" * 25,
            "BASIC_AUTH": "Basic " + basic,
            "JWT": jwt,
            "EMAIL_CANDIDATE": "synthetic@example.invalid",
            "KR_MOBILE_CANDIDATE": "010-0000-0000",
            "INLINE_MEDIA": "data:image/png;base64," + base64.b64encode(b"synthetic-media").decode(),
        }
        self.write([{"type": "message", "text": text} for text in examples.values()])
        before = self.source.read_bytes()
        code, stdout, stderr = self.run_cli()
        self.assertEqual((code, stderr), (0, ""))
        result = self.load_output()
        for event, kind in zip(result, examples):
            self.assertIn("REDACTED:", event["text"])
            self.assertIn(kind, event["text"])
        manifest = json.loads((self.output / SUT.MANIFEST).read_text())
        self.assertEqual(manifest["counts"]["events"], len(examples))
        self.assertEqual(manifest["counts"]["changed_leaves"], len(examples))
        self.assertEqual(manifest["input_sha256"], digest(before))
        self.assertEqual(manifest["candidate_sha256"], digest((self.output / SUT.CANDIDATE).read_bytes()))
        self.assertEqual(manifest["changes_sha256"], digest((self.output / SUT.CHANGES).read_bytes()))
        self.assertEqual(self.source.read_bytes(), before)
        audit_text = (self.output / SUT.CHANGES).read_text()
        for value in examples.values():
            self.assertNotIn(value, stdout + stderr + audit_text)
        self.assertEqual(manifest["review"]["corporate_source_coverage"], "NOT_PROVIDED")

    def test_negative_text_and_invalid_basic_remain(self):
        texts = ["한글 Goal 결과와 실패를 유지합니다.", "sk-short", "Basic invalid!",
                 "Basic " + base64.b64encode(b"no-colon-here").decode(),
                 "Bearer token", "1.2.3", "010-00-0000", "https://example.invalid/path"]
        self.write([{"text": x} for x in texts])
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual([x["text"] for x in self.load_output()], texts)

    def test_protected_metadata_and_opaque_are_unchanged(self):
        token = synthetic_key()
        fields = {k: token for k in ("timestamp", "id", "type", "role", "name", "model",
                                    "effort", "call_id", "session_id", "reasoning_effort")}
        fields.update({"encrypted_content": token, "payload": {"text": token}})
        self.write([fields])
        self.assertEqual(self.run_cli()[0], 0)
        result = self.load_output()[0]
        for key in fields:
            if key != "payload":
                self.assertEqual(result[key], fields[key])
        manifest = json.loads((self.output / SUT.MANIFEST).read_text())
        self.assertEqual(manifest["counts"]["unresolved_protected_leaves"], 10)
        self.assertEqual(manifest["counts"]["opaque_unreviewed_leaves"], 1)
        self.assertNotIn("encrypted_content", (self.output / SUT.CHANGES).read_text())
        original = SUT.redact_text
        def checked_redact(value, *args):
            self.assertNotEqual(value, token, "opaque leaf must not be scanned")
            return original(value, *args)
        with patch.object(SUT, "redact_text", side_effect=checked_redact):
            result, _, _ = transform(SUT, {"encrypted_content": {"nested": token}})
            self.assertEqual(result["encrypted_content"]["nested"], token)

    def test_policy_masks_whole_leaf_and_preserves_protected(self):
        leaf = "합성 회사자료 문장\n전체를 가립니다."
        leaf_hash = digest(leaf.encode("utf-8"))
        policy = self.root / "policy.json"
        policy.write_text(json.dumps({"redact_leaf_sha256": [leaf_hash]}), encoding="utf-8")
        self.write([{"text": leaf, "id": leaf, "encrypted_content": leaf, "other": leaf + " suffix"}])
        self.assertEqual(self.run_cli(["--policy", str(policy)])[0], 0)
        result = self.load_output()[0]
        self.assertEqual(result["text"], "[REDACTED:CORPORATE_SOURCE]")
        self.assertEqual((result["id"], result["encrypted_content"], result["other"]), (leaf, leaf, leaf + " suffix"))
        entries = [json.loads(x) for x in (self.output / SUT.CHANGES).read_text().splitlines()]
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["before_sha256"], leaf_hash)
        self.assertEqual(entries[0]["before_bytes"], len(leaf.encode("utf-8")))
        self.assertEqual(entries[0]["jsonpath"], "$.text")

    def test_structure_number_lexemes_event_order_and_last_line(self):
        raw = ('{"id":"one","n":-0,"f":1.234567890123456789,"large":1e999,"tiny":1e-999,'
               '"list":[true,false,null,123456789012345678901234567890],"text":"한글"}\r\n'
               '{"id":"two","children":[{"text":"ordinary"}],"empty":{}}').encode("utf-8")
        self.source.write_bytes(raw)
        self.assertEqual(self.run_cli()[0], 0)
        candidate = (self.output / SUT.CANDIDATE).read_bytes()
        self.assertIn(b'"f":1.234567890123456789', candidate)
        self.assertIn(b'"large":1e999', candidate)
        self.assertIn(b'"tiny":1e-999', candidate)
        self.assertIn(b'"n":-0', candidate)
        source_events = [SUT.parse_event(x) for x in raw.splitlines()]
        candidate_events = [SUT.parse_event(x) for x in candidate.splitlines()]
        self.assertEqual(len(source_events), len(candidate_events))
        for before, after in zip(source_events, candidate_events):
            SUT.assert_preserved(before, after, locked=True)
        self.assertEqual(self.source.read_bytes(), raw)

    def test_hash_scoped_store_literal_quotes_duplicates_and_unregistered(self):
        stores = ["SYN-LEGACY-A", "SYN-LEGACY-B", "SYN-LEGACY-C", "SYN-LEGACY-D"]
        forms = ['"storeCode": "{}"', "'storeCode': '{}'", "storeCode='{}'", 'STORECODE = "{}"']
        text = "\n".join(form.format(code) for form, code in zip(forms, stores))
        text += '\nstoreCode="SYN-LEGACY-A"\nstoreCode="SYN-UNREGISTERED"'
        policy = self.root / "policy.json"
        policy.write_text(json.dumps({"redact_leaf_sha256": [], "redact_store_code_sha256":
                                     [digest(x.encode("utf-8")) for x in stores]}), encoding="utf-8")
        self.write([{"text": text, "status": text, "encrypted_content": text,
                     "storeCode": stores[0], "error": {"type": "synthetic", "message": text}}])
        self.assertEqual(self.run_cli(["--policy", str(policy)])[0], 0)
        result = self.load_output()[0]
        self.assertEqual(result["text"].count("[REDACTED_LEGACY_STORE_ID]"), 5)
        self.assertIn('storeCode="SYN-UNREGISTERED"', result["text"])
        self.assertEqual(result["status"], text)
        self.assertEqual(result["encrypted_content"], text)
        self.assertEqual(result["storeCode"], stores[0])  # Only the explicit text literal grammar.
        self.assertEqual(result["error"]["type"], "synthetic")
        self.assertEqual(result["error"]["message"], result["text"])

    def test_inline_multimegabyte_media_and_pure_base64(self):
        large = "A" * (3 * 1024 * 1024)
        self.write([{"text": "before data:image/png;base64," + large + " after " + synthetic_key()},
                    {"type": "image", "data": "aGVsbG8="},
                    {"type": "audio", "data": {"payload": "YQ=="}},
                    {"type": "message", "text": "aGVsbG8="}])
        self.assertEqual(self.run_cli()[0], 0)
        result = self.load_output()
        self.assertEqual(result[0]["text"], "before [REDACTED:INLINE_MEDIA] after [REDACTED:OPENAI_KEY]")
        self.assertEqual(result[1]["data"], "[REDACTED:EMBEDDED_MEDIA]")
        self.assertEqual(result[2]["data"]["payload"], "[REDACTED:EMBEDDED_MEDIA]")
        self.assertEqual(result[3]["text"], "aGVsbG8=")

    def test_media_base64_lookalike_alt_and_caption_are_preserved(self):
        event = {"type": "image", "data": "aGVsbG8=", "alt": "test", "caption": "aGVsbG8="}
        result, entries, counts = transform(SUT, event)
        self.assertEqual(result["data"], "[REDACTED:EMBEDDED_MEDIA]")
        self.assertEqual(result["alt"], event["alt"])
        self.assertEqual(result["caption"], event["caption"])
        self.assertEqual(counts["changed_leaves"], 1)
        self.assertEqual(len(entries), 1)

    def test_untyped_png_base64_end_to_end_preserves_protected_and_opaque(self):
        png = synthetic_png()
        events = [{"type": "tool_result", "payload": {"item": {"result": png}}},
                  {"id": png, "encrypted_content": png, "text": "평범한 Goal 결과입니다."}]
        self.write(events)
        original = self.source.read_bytes()
        code, stdout, stderr = self.run_cli()
        self.assertEqual((code, stderr), (0, ""))
        result = self.load_output()
        self.assertEqual(result[0]["payload"]["item"]["result"], "[REDACTED:EMBEDDED_MEDIA]")
        self.assertEqual(result[1], events[1])
        manifest_text = (self.output / SUT.MANIFEST).read_text()
        audit_text = (self.output / SUT.CHANGES).read_text()
        self.assertNotIn(png, stdout + stderr + manifest_text + audit_text)
        counts = json.loads(manifest_text)["counts"]
        self.assertEqual(counts["changed_leaves"], 1)
        self.assertEqual(counts["unresolved_protected_leaves"], 1)
        self.assertEqual(counts["opaque_unreviewed_leaves"], 1)
        self.assertEqual(self.source.read_bytes(), original)

    def test_untyped_base64_without_png_magic_and_malformed_png_are_preserved(self):
        cases = ["test", "aGVsbG8=", base64.b64encode(b"ordinary English description").decode(),
                 synthetic_png() + "!", synthetic_png()[:-1], "description " + synthetic_png(),
                 base64.b64encode(b"\x89PNX\r\n\x1a\nordinary").decode()]
        for value in cases:
            with self.subTest(length=len(value)):
                event = {"text": value, "alt": value, "caption": value}
                result, entries, counts = transform(SUT, event)
                self.assertEqual(result, event)
                self.assertEqual(entries, [])
                self.assertEqual(counts["changed_leaves"], 0)

    def test_camel_pascal_id_fields_and_arrays_preserve_suspicious_values(self):
        png, token = synthetic_png(), synthetic_key()
        event = {"threadId": png, "responseId": token, "callId": png, "nestedID": token,
                 "ThreadId": png, "ResponseID": token, "APIId": png,
                 "threadIds": [png, token], "callIDs": [token], "Ids": [png], "ids": [png],
                 "nested": {"responseID": png}, "encrypted_content": png}
        result, entries, counts = transform(SUT, event)
        self.assertEqual(result, event)
        self.assertEqual(counts["changed_leaves"], 0)
        self.assertEqual(counts["unresolved_protected_leaves"], 13)
        self.assertEqual(counts["opaque_unreviewed_leaves"], 1)
        self.assertEqual(len(entries), 13)
        self.assertTrue(all(e["kind"].startswith("UNRESOLVED_PROTECTED:") for e in entries))
        self.assertNotIn(png, json.dumps(entries))
        self.assertNotIn(token, json.dumps(entries))

    def test_id_suffix_boundary_does_not_protect_ordinary_words(self):
        event = {key: synthetic_key() for key in ("grid", "valid", "solid", "fluid", "Grid", "VALID", "GRID")}
        result, entries, counts = transform(SUT, event)
        self.assertEqual(list(result), list(event))
        self.assertTrue(all(value == "[REDACTED:OPENAI_KEY]" for value in result.values()))
        self.assertEqual(counts["changed_leaves"], len(event))
        self.assertEqual(counts["unresolved_protected_leaves"], 0)
        self.assertEqual(len(entries), len(event))

    def test_suspicious_object_key_is_preserved_and_unresolved(self):
        key = synthetic_key()
        event = {key: "ordinary text"}
        result, entries, counts = transform(SUT, event)
        self.assertEqual(result, event)
        self.assertEqual(counts["changed_leaves"], 0)
        self.assertEqual(counts["unresolved_key_count"], 1)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["kind"], "UNRESOLVED_KEY:OPENAI_KEY")
        self.assertEqual(entries[0]["before_sha256"], digest(key.encode("utf-8")))
        self.assertEqual(entries[0]["before_sha256"], entries[0]["after_sha256"])
        self.assertNotIn(key, json.dumps(entries))
        self.assertIn("key-sha256=", entries[0]["jsonpath"])

    def test_korean_adjacent_credentials_and_email_end_to_end(self):
        jwt = ".".join(base64.urlsafe_b64encode(x).decode().rstrip("=") for x in
                       (b'{"alg":"HS256"}', b'{"sub":"SYNTHETIC"}', b"synthetic-signature"))
        tokens = [synthetic_key(), "ghp_" + "S" * 36, "synthetic@example.invalid",
                  "Bearer " + "S" * 24,
                  "Basic " + base64.b64encode(b"synthetic-user:synthetic-password").decode(),
                  jwt, "aws_secret_access_key=" + "S" * 40,
                  "https://synthetic:password@example.invalid/path", "AKIA" + "S" * 16]
        wrappers = [("키는", ""), ("", "입니다"), ("키는", "입니다"), ("키는 ", " 입니다")]
        events = [{"text": prefix + token + suffix}
                  for token in tokens for prefix, suffix in wrappers]
        self.write(events)
        code, stdout, stderr = self.run_cli()
        self.assertEqual((code, stderr), (0, ""))
        results = self.load_output()
        for index, event in enumerate(results):
            token = tokens[index // len(wrappers)]
            prefix, suffix = wrappers[index % len(wrappers)]
            self.assertNotIn(token, event["text"])
            self.assertTrue(event["text"].startswith(prefix))
            self.assertTrue(event["text"].endswith(suffix))
            self.assertIn("[REDACTED:", event["text"])
            self.assertNotIn(token, stdout)
        manifest = json.loads((self.output / SUT.MANIFEST).read_text())
        self.assertEqual(manifest["counts"]["changed_leaves"], len(events))
        self.assertEqual(len(results), len(events))

    def test_failure_inputs_have_no_completion_manifest_or_raw_error(self):
        cases = [b"", b"\n", b"{}\n\n", b"[]\n", b"null\n", b"42\n",
                 b'{"x":1,"x":2}\n', b'{"nested":{"x":1,"x":2}}\n',
                 b'{"x":NaN}\n', b'{"x":Infinity}\n', b'\xef\xbb\xbf{}\n',
                 b'{"text":"SYNTHETIC-SENSITIVE-ERROR", broken}\n', b'{}\n{"partial":',
                 b'{"text":"\xff"}\n', b'{"text":"\\ud800"}\n']
        for index, raw in enumerate(cases):
            with self.subTest(index=index):
                self.source.write_bytes(raw)
                self.output = self.root / f"bad-{index}"
                code, stdout, stderr = self.run_cli()
                self.assertEqual(code, 2)
                self.assertEqual(stdout, "")
                self.assertRegex(stderr, r"^ERROR:[A-Z_]+\n$")
                self.assertNotIn("SYNTHETIC-SENSITIVE-ERROR", stderr)
                self.assertFalse((self.output / SUT.MANIFEST).exists())
                self.assertEqual(self.source.read_bytes(), raw)

    def test_existing_output_and_outside_local_are_rejected(self):
        self.write([{}])
        self.output.mkdir()
        sentinel = self.output / "keep"
        sentinel.write_text("synthetic sentinel")
        self.assertEqual(self.run_cli()[0], 2)
        self.assertEqual(sentinel.read_text(), "synthetic sentinel")
        self.output = SUT.LOCAL_ROOT.parent / "submission-forbidden-output"
        self.assertEqual(self.run_cli()[0], 2)
        self.assertFalse(self.output.exists())

    def test_hardlinked_input_rejected(self):
        self.write([{}])
        alias = self.root / "alias.jsonl"
        os.link(self.source, alias)
        self.assertEqual(self.run_cli()[0], 2)
        self.assertFalse(self.output.exists())

    def test_reparse_path_guard(self):
        fake = types.SimpleNamespace(st_mode=0, st_file_attributes=0x400)
        with patch.object(Path, "lstat", return_value=fake):
            with self.assertRaisesRegex(SUT.PreparationError, "LINK_PATH_REJECTED"):
                SUT.no_links(self.root)

    def test_actual_symlink_rejected_when_supported(self):
        self.write([{}])
        link = self.root / "symlink.jsonl"
        try:
            os.symlink(self.source, link)
        except OSError:
            self.skipTest("OS cannot create symlink; reparse and actual hardlink controls still run")
        self.source = link
        self.assertEqual(self.run_cli()[0], 2)

    def test_input_change_during_processing_is_rejected(self):
        self.write([{"text": "ordinary"}])
        original = SUT.transform
        changed = False

        def mutate(*args, **kwargs):
            nonlocal changed
            if not changed:
                changed = True
                with self.source.open("ab") as handle:
                    handle.write(b'{}\n')
            return original(*args, **kwargs)

        with patch.object(SUT, "transform", side_effect=mutate):
            self.assertEqual(self.run_cli()[0], 2)
        self.assertFalse((self.output / SUT.MANIFEST).exists())

    def test_invalid_policy_rejected_without_values(self):
        self.write([{}])
        policies = ["not-json", '{"redact_leaf_sha256":["sensitive-invalid"]}',
                    '{"wrong":[]}', '{"redact_leaf_sha256":[],"redact_leaf_sha256":[]}']
        policy = self.root / "policy.json"
        for raw in policies:
            policy.write_text(raw, encoding="utf-8")
            code, stdout, stderr = self.run_cli(["--policy", str(policy)])
            self.assertEqual((code, stdout), (2, ""))
            self.assertNotIn("sensitive-invalid", stderr)
            self.assertFalse(self.output.exists())

    def test_cli_argument_error_does_not_echo_value(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = SUT.main(["--unknown", synthetic_key()])
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "ERROR:INVALID_ARGUMENTS\n")

    def test_suspicious_object_key_never_appears_in_audit(self):
        key = "github_pat_" + "S" * 30
        self.write([{key: synthetic_key()}])
        self.assertEqual(self.run_cli()[0], 0)
        self.assertIn(key, self.load_output()[0])
        audit = (self.output / SUT.CHANGES).read_text()
        self.assertNotIn(key, audit)
        self.assertIn("key-sha256=", audit)


class MutationControls(unittest.TestCase):
    """Each original probe passes; each single behavior mutation must fail it."""

    @staticmethod
    def load(source):
        module = types.ModuleType("submission_mutant")
        module.__file__ = str(SCRIPT)
        exec(compile(source, str(SCRIPT), "exec"), module.__dict__)
        return module

    def test_masking_protection_and_record_guard_mutations_are_killed(self):
        source = SCRIPT.read_text(encoding="utf-8")

        def mask_probe(module):
            result, _, _ = transform(module, {"text": synthetic_key()})
            self.assertEqual(result["text"], "[REDACTED:OPENAI_KEY]")

        def protection_probe(module):
            result, _, counts = transform(module, {"id": synthetic_key()})
            self.assertEqual(result["id"], synthetic_key())
            self.assertEqual(counts["unresolved_protected_leaves"], 1)

        def record_probe(module):
            with self.assertRaises(module.PreparationError):
                module.assert_preserved({"text": "x", "id": "one"}, {"text": "x"})

        def duplicate_probe(module):
            with self.assertRaises(module.PreparationError):
                module.parse_event(b'{"id":"one","id":"two"}')

        def media_field_probe(module):
            result, _, counts = transform(module, {"type": "image", "data": "aGVsbG8=", "alt": "test"})
            self.assertEqual(result["alt"], "test")
            self.assertEqual(counts["changed_leaves"], 1)

        def suspicious_key_probe(module):
            result, entries, counts = transform(module, {synthetic_key(): "ordinary"})
            self.assertEqual(counts["unresolved_key_count"], 1)
            self.assertEqual(entries[0]["kind"], "UNRESOLVED_KEY:OPENAI_KEY")

        def korean_boundary_probe(module):
            result, _, _ = transform(module, {"text": "키는" + synthetic_key() + "입니다"})
            self.assertEqual(result["text"], "키는[REDACTED:OPENAI_KEY]입니다")

        def untyped_png_probe(module):
            result, _, _ = transform(module, {"payload": {"item": {"result": synthetic_png()}}})
            self.assertEqual(result["payload"]["item"]["result"], "[REDACTED:EMBEDDED_MEDIA]")

        def png_magic_probe(module):
            value = base64.b64encode(b"ordinary English description").decode()
            result, _, _ = transform(module, {"caption": value})
            self.assertEqual(result["caption"], value)

        def png_complete_base64_probe(module):
            value = synthetic_png() + "!"
            result, _, _ = transform(module, {"text": value})
            self.assertEqual(result["text"], value)

        def camel_id_probe(module):
            event = {"threadId": synthetic_png()}
            result, _, counts = transform(module, event)
            self.assertEqual(result, event)
            self.assertEqual(counts["unresolved_protected_leaves"], 1)

        def id_boundary_probe(module):
            result, _, counts = transform(module, {"valid": synthetic_key()})
            self.assertEqual(result["valid"], "[REDACTED:OPENAI_KEY]")
            self.assertEqual(counts["unresolved_protected_leaves"], 0)

        mutations = [
            ("masking", 'return "".join(result), sorted(kinds)', 'return value, []', mask_probe),
            ("protection", "locked = inherited_protection or protected(key)", "locked = False", protection_probe),
            ("record_guard", "def assert_preserved(before, after, locked=False):", "def assert_preserved(before, after, locked=False):\n    return", record_probe),
            ("duplicate_key", 'raise PreparationError("DUPLICATE_JSON_KEY")', "pass", duplicate_probe),
            ("media_field_guard", "media and key.lower() in MEDIA_PAYLOAD_FIELDS", "media", media_field_probe),
            ("unresolved_key_guard", "if key_kinds:", "if False:", suspicious_key_probe),
            ("unicode_boundary", "(?<![A-Za-z0-9_-])sk-", r"(?<![\w-])sk-", korean_boundary_probe),
            ("untyped_png", "if (media and pure_base64(value)) or png_base64(value):",
             "if media and pure_base64(value):", untyped_png_probe),
            ("png_magic", 'return header.startswith(b"\\x89PNG\\r\\n\\x1a\\n") and pure_base64(value)',
             "return pure_base64(value)", png_magic_probe),
            ("png_complete_base64", 'return header.startswith(b"\\x89PNG\\r\\n\\x1a\\n") and pure_base64(value)',
             'return header.startswith(b"\\x89PNG\\r\\n\\x1a\\n")', png_complete_base64_probe),
            ("camel_id_protection", " or camel_id", "", camel_id_probe),
            ("id_suffix_boundary", " or camel_id", ' or lowered.endswith("id")', id_boundary_probe),
        ]
        for name, before, after, probe in mutations:
            with self.subTest(mutation=name):
                self.assertEqual(source.count(before), 1)
                probe(self.load(source))  # CONTROL uses identical loading/location.
                with self.assertRaises(AssertionError):
                    probe(self.load(source.replace(before, after, 1)))


if __name__ == "__main__":
    unittest.main()
