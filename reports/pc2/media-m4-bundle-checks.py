"""N02-M4 synthetic delivery tests. No npm, download, socket, key or deployment."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import build_deployment_bundle as bundle
from scripts import fetch_demo_media as fetcher
from server.media_contract import (MEDIA_NAMES, TRACKS_NAME, TRACKS_URL,
                                   TRACKS_SCHEMA, CURRENT_RELEASE_TAG,
                                   validate_media_manifest)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def put(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data.encode() if isinstance(data, str) else data)
    return path


class DeliveryChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pc2-m4-bundle-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'synthetic-source'
        self.root.mkdir()
        self.payloads = {name: ('SYNTHETIC-ONLY:' + name).encode() for name in MEDIA_NAMES}
        self.payloads[TRACKS_NAME] = b'{"synthetic":true,"frames":[]}'
        assets = [{'name': name, 'bytes': len(self.payloads[name]),
                   'sha256': sha(self.payloads[name]), 'synthetic': True} for name in MEDIA_NAMES]
        self.manifest = {'schemaVersion': 1, 'repository': 'cjj0202-glitch/happycall-ralphthon',
                         'releaseTag': CURRENT_RELEASE_TAG, 'assets': assets}
        self.manifest_path = self.root / bundle.MEDIA_MANIFEST
        for name in bundle.SOURCE_FILES:
            put(self.root, name, '# synthetic source\n' if name.endswith('.py') else '{}\n')
        for name in bundle.TEMPLATES:
            put(self.root, name, (ROOT / name).read_bytes())
        put(self.root, 'pyproject.toml', '[project]\nname="synthetic-m4"\nversion="0.0.0"\nrequires-python=">=3.12,<3.13"\n')
        put(self.root, 'uv.lock', 'version=1\nrevision=1\nrequires-python=">=3.12,<3.13"\n')
        cases = '[{"synthetic":true,"id":"SYN-M4-ONLY"}]\n'
        for name in ['data/fixtures/cases.json', 'apps/web/public/cases.json', 'apps/web/out/cases.json']:
            put(self.root, name, cases)
        put(self.root, 'data/overlays/pc4-tms.json', '{"synthetic":true}\n')
        for name, data in {
            'package.json': '{"name":"synthetic","scripts":{"build":"next build"}}',
            'package-lock.json': '{"name":"synthetic","lockfileVersion":3}',
            'tsconfig.json': '{}', 'next.config.ts': 'export default {output:"export"};',
            'app/page.tsx': 'export default function Page(){return "synthetic"}',
            'app/layout.tsx': 'export default function Layout(){return "synthetic"}',
            'lib/api.ts': 'export const API_BASE="";',
            'out/index.html': '<!doctype html><main>synthetic</main>',
            'out/404.html': '<!doctype html>not found', 'out/index.txt': 'synthetic-flight',
            'out/_next/static/chunks/app.js': 'self.synthetic=true;',
            'out/_next/static/css/app.css': 'body{color:black;}',
        }.items():
            put(self.root, 'apps/web/' + name, data)
        self.write_manifest()
        self.install()

    def write_manifest(self):
        put(self.root, bundle.MEDIA_MANIFEST, json.dumps(self.manifest))

    def register(self):
        self.manifest['assets'][2]['tracks'] = {
            'schemaVersion': TRACKS_SCHEMA, 'url': TRACKS_URL,
            'bytes': len(self.payloads[TRACKS_NAME]), 'sha256': sha(self.payloads[TRACKS_NAME]),
            'videoSha256': self.manifest['assets'][2]['sha256']}
        self.write_manifest()
        self.install()

    def install(self):
        # Inject bytes; never use gh or network. Build export is a declared
        # synthetic fixture, not an actual npm/Next build.
        assets = fetcher.validate_manifest(self.manifest)
        def synthetic_download(name, directory):
            (directory / name).write_bytes(self.payloads[name])
        fetcher.fetch(assets, self.root / 'apps/web/public/demo', downloader=synthetic_download)
        for asset in assets:
            put(self.root, 'apps/web/out/demo/' + asset['name'], self.payloads[asset['name']])

    def stamp(self):
        return bundle.write_build_stamp(self.root, bundle.source_fingerprint(self.root))

    def package(self):
        return bundle.build_bundle(self.root, self.manifest_path,
                                   timestamp='20260921T140000000000Z', revision='c' * 40)

    def no_complete(self):
        self.assertFalse(list((self.root / 'dist').rglob('.bundle-manifest.json')))

    def test_existing_three_assets_preserve_exact_inventory(self):
        self.stamp()
        out = self.package()
        for name in MEDIA_NAMES:
            for folder in ['apps/web/public/demo/', 'apps/web/out/demo/']:
                self.assertEqual((out / (folder + name)).read_bytes(), self.payloads[name])
        self.assertFalse((out / 'apps/web/out/demo' / TRACKS_NAME).exists())
        self.assertTrue((out / 'server/media_contract.py').is_file())

    def test_registered_sidecar_fetch_public_export_package_identical(self):
        self.register()
        self.stamp()
        out = self.package()
        for base in [self.root, out]:
            for folder in ['apps/web/public/demo/', 'apps/web/out/demo/']:
                data = (base / (folder + TRACKS_NAME)).read_bytes()
                self.assertEqual(data, self.payloads[TRACKS_NAME])
                self.assertEqual(sha(data), self.manifest['assets'][2]['tracks']['sha256'])
        inventory = json.loads((out / '.bundle-manifest.json').read_bytes())['files']
        self.assertEqual(sum(x['path'].endswith(TRACKS_NAME) for x in inventory), 2)

    def test_unregistered_sidecar_is_not_allowed_in_export(self):
        put(self.root, 'apps/web/out/demo/' + TRACKS_NAME, self.payloads[TRACKS_NAME])
        with self.assertRaisesRegex(bundle.BundleError, 'UNAPPROVED_EXPORT_FILE'):
            self.stamp()
        self.no_complete()

    def test_extra_json_not_allowed_even_with_registration(self):
        self.register()
        put(self.root, 'apps/web/out/demo/other.json', '{}')
        with self.assertRaisesRegex(bundle.BundleError, 'UNAPPROVED_EXPORT_FILE'):
            self.stamp()

    def test_registered_missing_public_sidecar_fails(self):
        self.register()
        (self.root / 'apps/web/public/demo' / TRACKS_NAME).unlink()
        with self.assertRaises((bundle.BundleError, OSError)):
            self.stamp()
        self.no_complete()

    def test_registered_missing_export_sidecar_fails(self):
        self.register()
        (self.root / 'apps/web/out/demo' / TRACKS_NAME).unlink()
        with self.assertRaisesRegex(bundle.BundleError, 'INCOMPLETE_NEXT_EXPORT'):
            self.stamp()

    def test_same_size_corruption_fails_sha(self):
        self.register()
        for folder in ['apps/web/public/demo/', 'apps/web/out/demo/']:
            put(self.root, folder + TRACKS_NAME, b'x' * len(self.payloads[TRACKS_NAME]))
        with self.assertRaisesRegex(bundle.BundleError, 'MEDIA_BYTES_OR_HASH_MISMATCH'):
            self.stamp()

    def test_export_different_from_public_fails(self):
        self.register()
        put(self.root, 'apps/web/out/demo/' + TRACKS_NAME, b'x' * len(self.payloads[TRACKS_NAME]))
        with self.assertRaisesRegex(bundle.BundleError, 'MEDIA_BYTES_OR_HASH_MISMATCH'):
            self.stamp()

    def test_registered_parent_video_corruption_fails(self):
        self.register()
        name = 'sorter-demo.mp4'
        for folder in ['apps/web/public/demo/', 'apps/web/out/demo/']:
            put(self.root, folder + name, b'x' * len(self.payloads[name]))
        with self.assertRaisesRegex(bundle.BundleError, 'MEDIA_BYTES_OR_HASH_MISMATCH'):
            self.stamp()

    def test_manifest_change_invalidates_existing_stamp(self):
        self.stamp()
        self.register()
        with self.assertRaisesRegex(bundle.BundleError, 'STALE_OR_CHANGED_BUILD_STAMP'):
            self.package()
        self.no_complete()

    def test_noncanonical_manifest_rejected(self):
        self.register()
        self.stamp()
        other = put(self.root, 'other.json', self.manifest_path.read_bytes())
        with self.assertRaisesRegex(bundle.BundleError, 'CANONICAL_MEDIA_MANIFEST_REQUIRED'):
            bundle.build_bundle(self.root, other, timestamp='20260921T140000000000Z', revision='c'*40)

    def test_invalid_descriptor_matrix(self):
        self.register()
        mutations = [('schemaVersion','wrong'), ('url','/demo/../other.json'),
                     ('url','https://example.invalid/x'), ('url', TRACKS_URL+'?v=1'),
                     ('bytes', True), ('bytes', 0), ('bytes', -1), ('bytes', 10_000_001),
                     ('sha256','A'*64), ('sha256','0'*63), ('videoSha256','0'*64),
                     ('unexpected', True)]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                m = copy.deepcopy(self.manifest)
                m['assets'][2]['tracks'][field] = value
                with self.assertRaises(ValueError):
                    validate_media_manifest(m, require_synthetic=True)

    def test_tracks_on_audio_or_top_level_fourth_asset_fails(self):
        self.register()
        m=copy.deepcopy(self.manifest)
        m['assets'][0]['tracks']=m['assets'][2].pop('tracks')
        with self.assertRaises(ValueError): validate_media_manifest(m)
        m=copy.deepcopy(self.manifest)
        m['assets'].append({'name': TRACKS_NAME, 'bytes': 10, 'sha256': 'a'*64})
        with self.assertRaises(ValueError): validate_media_manifest(m)

    def test_bad_release_values_fail_consistently_for_download_contract(self):
        for tag in [[], {}, None, 'arbitrary-release']:
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                validate_media_manifest({**self.manifest,'releaseTag':tag})

    def test_offline_legacy_three_assets_only_sidecar_still_requires_approved_tag(self):
        legacy={**self.manifest,'releaseTag':'demo-media-20260921'}
        self.assertEqual(len(validate_media_manifest(legacy,check_release=False)),3)
        self.register()
        legacy={**self.manifest,'releaseTag':'demo-media-20260921'}
        with self.assertRaisesRegex(ValueError,'UNAPPROVED_TRACKS_RELEASE'):
            validate_media_manifest(legacy,check_release=False)

    def test_hardlinked_sidecar_rejected_without_changing_target(self):
        self.register()
        p=self.root/'apps/web/public/demo'/TRACKS_NAME
        before=p.read_bytes()
        external=put(self.root,'outside-original',before)
        p.unlink()
        os.link(external,p)
        with self.assertRaisesRegex(bundle.BundleError,'LINK_PATH_REJECTED'): self.stamp()
        self.assertEqual(external.read_bytes(),before)

    def test_symlink_sidecar_rejected_without_changing_target(self):
        self.register()
        p=self.root/'apps/web/public/demo'/TRACKS_NAME
        before=p.read_bytes()
        external=put(self.root,'outside-original',before)
        p.unlink()
        try: p.symlink_to(external)
        except OSError as exc:
            if getattr(exc,'winerror',None)==1314: self.skipTest('Windows symlink privilege unavailable')
            raise
        with self.assertRaisesRegex(bundle.BundleError,'LINK_PATH_REJECTED'): self.stamp()
        self.assertEqual(external.read_bytes(),before)

    def test_package_write_failure_preserves_source_and_no_complete_marker(self):
        self.register()
        self.stamp()
        source=(self.root/'apps/web/public/demo'/TRACKS_NAME).read_bytes()
        original=Path.open
        def fail(path, mode='r', *args, **kwargs):
            if 'dist' in path.parts and path.name==TRACKS_NAME and mode=='xb':
                raise OSError('synthetic output failure')
            return original(path,mode,*args,**kwargs)
        with patch.object(Path,'open',fail), self.assertRaisesRegex(bundle.BundleError,'BUNDLE_WRITE_FAILED'):
            self.package()
        self.assertEqual((self.root/'apps/web/public/demo'/TRACKS_NAME).read_bytes(),source)
        self.no_complete()


if __name__=='__main__':
    unittest.main(verbosity=2)
