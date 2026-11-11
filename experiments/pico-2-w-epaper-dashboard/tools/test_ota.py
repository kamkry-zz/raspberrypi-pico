"""Host tests for OTA: boot selection/rollback, verification, update flow.

``ota.check()`` runs end to end against a local fake of the iot-registry
device API; slots and state live in a temporary directory.
"""

import hashlib
import hmac
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "tools"))

import build as builder  # noqa: E402
import config  # noqa: E402
import ota  # noqa: E402
import ota_publish  # noqa: E402
import otaboot  # noqa: E402

KEY = os.urandom(32).hex()
MP = otaboot.micropython_version()


def release(build, files, key=KEY, **target):
    manifest = ota_publish.make_manifest(files, build, "0.%d.0" % build, "test")
    if target:
        data = json.loads(manifest)
        data["target"].update(target)
        manifest = json.dumps(data).encode()
    else:  # pretend the publisher targets the MicroPython running these tests
        data = json.loads(manifest)
        data["target"]["micropython"] = MP
        manifest = json.dumps(data).encode()
    return manifest, ota_publish.sign(manifest, key), {hashlib.sha256(d).hexdigest(): d for _, d in files}


class FakeRegistry:
    def __init__(self):
        self.manifest = None
        self.signature = ""
        self.files = {}
        self.reports = []
        registry = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path.endswith("/manifest"):
                    if registry.manifest is None:
                        return self._send(404, b"{}")
                    build = json.loads(registry.manifest)["build"]
                    if self.headers.get("If-None-Match") == '"%d"' % build:
                        return self._send(304, b"")
                    return self._send(200, registry.manifest, {"ETag": '"%d"' % build})
                if self.path.endswith("/manifest.sig"):
                    return self._send(200, registry.signature.encode())
                sha = self.path.rsplit("/", 1)[-1]
                if sha in registry.files:
                    return self._send(200, registry.files[sha])
                return self._send(404, b"{}")

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                registry.reports.append(json.loads(self.rfile.read(length)))
                self._send(202, b"{}")

            def _send(self, code, body, headers=None):
                self.send_response(code)
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d/ota/v1" % self.server.server_address[1]

    def publish(self, manifest, signature, files):
        self.manifest, self.signature = manifest, signature
        self.files.update(files)

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class OtaTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.patches = {
            (otaboot, "ROOT"): self.tmp + "/ota",
            (otaboot, "STATE_FILE"): self.tmp + "/ota/state.json",
            (otaboot, "MAINT_FLAG"): self.tmp + "/maint",
            (otaboot, "_key_held"): lambda pin: False,
            (ota, "_rmtree"): lambda path: shutil.rmtree(path, ignore_errors=True),
            (ota, "_device"): lambda: "98:fe:54:1a:80:d7",
            (ota, "_secrets"): lambda: type("S", (), {"OTA_KEY": KEY}),
        }
        self.saved = {k: getattr(*k) for k in self.patches}
        for (obj, name), value in self.patches.items():
            setattr(obj, name, value)
        self.registry = FakeRegistry()
        self.saved_url = config.OTA_BASE_URL
        config.OTA_BASE_URL = self.registry.url
        self.saved_path = list(sys.path)
        otaboot.selected.update({"state": "factory", "slot": None, "build": None, "version": None, "reason": ""})
        ota.results.clear()

    def tearDown(self):
        for (obj, name), value in self.saved.items():
            setattr(obj, name, value)
        config.OTA_BASE_URL = self.saved_url
        sys.path[:] = self.saved_path
        self.registry.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def boot(self):
        sys.path[:] = self.saved_path
        otaboot.selected.update({"state": "factory", "slot": None, "build": None, "version": None, "reason": ""})
        return otaboot.select()

    def install(self, build, files=None):
        files = files or [("config.mpy", b"cfg%d" % build), ("lib/app.mpy", b"app%d" % build)]
        self.registry.publish(*release(build, files))
        resets = []
        result = ota.check(reset=lambda: resets.append(True))
        return result, resets


class VerificationTests(unittest.TestCase):
    def test_hmac_matches_python(self):
        for key in (b"k", os.urandom(32), os.urandom(100)):
            msg = os.urandom(300)
            self.assertEqual(ota.hmac_sha256(key, msg), hmac.new(key, msg, hashlib.sha256).digest())

    def test_verify_publisher_signature(self):
        manifest, signature, _ = release(1, [("lib/app.mpy", b"x")])
        self.assertTrue(ota.verify(manifest, signature, KEY))
        self.assertFalse(ota.verify(manifest + b" ", signature, KEY))
        self.assertFalse(ota.verify(manifest, signature, os.urandom(32).hex()))
        self.assertFalse(ota.verify(manifest, signature, ""))

    def test_safe_paths(self):
        for good in ("config.mpy", "lib/app.mpy", "lib/font_xlarge.mpy"):
            self.assertTrue(ota._safe_path(good), good)
        for bad in ("secrets.py", "main.py", "lib/otaboot.mpy", "lib/ota.mpy", "lib/../x.mpy",
                    "/lib/app.mpy", "lib/app.py", "certs/k3s-ca.der", "lib/a-b.mpy", "lib/.mpy"):
            self.assertFalse(ota._safe_path(bad), bad)

    def test_problem_checks(self):
        manifest = json.loads(release(5, [("lib/app.mpy", b"x")])[0])
        self.assertIsNone(ota.problem(manifest, {}, MP))
        self.assertEqual(ota.problem(manifest, {"active": {"build": 5}}, MP), "not newer")
        self.assertEqual(ota.problem(manifest, {"blacklist": [5]}, MP), "blacklisted")
        self.assertEqual(ota.problem(manifest, {}, "0.0.1"), "micropython")
        self.assertEqual(ota.problem(dict(manifest, app="other"), {}, MP), "app")
        bad = dict(manifest, files=[{"path": "secrets.py", "size": 1, "sha256": "0" * 64}])
        self.assertEqual(ota.problem(bad, {}, MP), "path")


class BootTests(OtaTestBase):
    def test_factory_without_state(self):
        self.assertEqual(self.boot()["state"], "factory")

    def test_install_trial_commit_then_rollback_of_next_build(self):
        result, resets = self.install(1)
        self.assertEqual((result, resets), ("updated", [True]))
        self.assertEqual([r["event"] for r in self.registry.reports], ["installed"])
        sel = self.boot()
        self.assertEqual((sel["state"], sel["slot"], sel["build"]), ("trial", "a", 1))
        self.assertEqual(sys.path[:2], [self.tmp + "/ota/a", self.tmp + "/ota/a/lib"])
        self.assertTrue(otaboot.commit())
        self.assertEqual(ota.check(), "none")  # flushes "committed"; manifest unchanged
        self.assertEqual(self.registry.reports[-1]["event"], "committed")

        # build 2 lands in slot b but never commits: 3 trial boots, then rollback
        self.assertEqual(self.install(2)[0], "updated")
        for attempt in range(otaboot.MAX_ATTEMPTS):
            self.assertEqual(self.boot()["state"], "trial", attempt)
        sel = self.boot()
        self.assertEqual((sel["state"], sel["slot"], sel["build"]), ("active", "a", 1))
        state = otaboot.load()
        self.assertIn(2, state["blacklist"])
        self.assertIsNone(state["trial"])
        self.assertEqual(ota.check(), "none")  # flushes rolled_back; build 2 is blacklisted
        self.assertEqual(self.registry.reports[-1]["event"], "rolled_back")
        self.assertEqual(self.registry.reports[-1]["build"], 2)

    def test_maintenance_boot_does_not_count(self):
        self.install(1)
        Path(self.tmp + "/maint").write_text("1")
        for _ in range(otaboot.MAX_ATTEMPTS + 2):
            self.assertEqual(self.boot()["state"], "trial")
        self.assertEqual(otaboot.load()["attempts"], 0)

    def test_key1_boots_factory(self):
        self.install(1)
        otaboot._key_held = lambda pin: pin == otaboot.KEY_FACTORY
        self.assertEqual(self.boot()["state"], "factory")
        self.assertEqual(otaboot.load()["attempts"], 0)

    def test_firmware_change_drops_slot(self):
        self.install(1)
        self.boot()
        otaboot.commit()
        state = otaboot.load()
        state["active"]["micropython"] = "0.0.1"
        otaboot.save(state)
        sel = self.boot()
        self.assertEqual(sel["state"], "factory")
        self.assertIn("unusable", sel["reason"])

    def test_corrupt_state_boots_factory(self):
        os.makedirs(self.tmp + "/ota", exist_ok=True)
        Path(otaboot.STATE_FILE).write_text("{not json")
        self.assertEqual(self.boot()["state"], "factory")


class CheckTests(OtaTestBase):
    def test_bad_signature_reported_once(self):
        manifest, _, files = release(1, [("lib/app.mpy", b"x")])
        self.registry.publish(manifest, "0" * 64, files)
        self.assertEqual(ota.check(), "bad_signature")
        self.assertEqual(ota.check(), "bad_signature")
        self.assertEqual([r["event"] for r in self.registry.reports], ["failed"])
        self.assertIsNone(otaboot.load().get("trial"))

    def test_hash_mismatch_keeps_running_slot(self):
        manifest, signature, files = release(1, [("lib/app.mpy", b"good")])
        self.registry.publish(manifest, signature, {sha: b"evil" for sha in files})
        self.assertEqual(ota.check(), "hash_mismatch")
        self.assertFalse(os.path.exists(self.tmp + "/ota/a"))
        self.assertIsNone(otaboot.load().get("trial"))

    def test_incompatible_firmware(self):
        self.registry.publish(*release(1, [("lib/app.mpy", b"x")], micropython="9.9.9"))
        self.assertEqual(ota.check(), "incompatible")

    def test_no_release_and_etag(self):
        self.assertEqual(ota.check(), "none")
        self.install(1)
        self.boot()
        otaboot.commit()
        self.assertEqual(ota.check(), "none")
        self.assertEqual(otaboot.load()["etag"], '"1"')

    def test_trial_pending_skips_check(self):
        self.install(1)
        self.assertEqual(ota.check(), "trial_pending")


class LayoutTests(unittest.TestCase):
    def test_slot_root_cannot_shadow_a_module(self):
        # MicroPython imports bare directories as packages and '' precedes
        # '.frozen': a root named like a module ("/ota") hid the frozen updater.
        name = otaboot.ROOT.strip("/")
        self.assertFalse(name.isidentifier(), otaboot.ROOT)


class PublisherTests(unittest.TestCase):
    def test_bundle_excludes_protected_and_matches_firmware_manifest(self):
        frozen = []
        text = (ROOT / "firmware" / "manifest.py").read_text()
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('"') and line.rstrip(",").endswith('"') or line.startswith('"') and "#" in line:
                frozen.append(line.split('"')[1])
        self.assertEqual(sorted(frozen), sorted(builder.LIBS))
        self.assertEqual(set(builder.OTA_PROTECTED), {"ota", "otaboot"})

    def test_manifest_is_canonical(self):
        files = [("config.mpy", b"c"), ("lib/app.mpy", b"a")]
        one = ota_publish.make_manifest(files, 3, "0.4.0", "n")
        two = ota_publish.make_manifest(files, 3, "0.4.0", "n")
        self.assertEqual(one, two)
        data = json.loads(one)
        self.assertEqual(data["target"]["board"], "RPI_PICO2_W")
        self.assertEqual([f["path"] for f in data["files"]], ["config.mpy", "lib/app.mpy"])


if __name__ == "__main__":
    unittest.main()
