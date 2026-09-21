"""Release-gate mutation controls only: no app/server/browser/model execution."""
from __future__ import annotations
import copy
import json
import unittest
from q2_contract import BOUNDARY_IDS, REQUIRED_SELECTORS, aggregate_guard, build_provenance_errors, required_inputs, safe_name


def valid_contract():
    return {'schema': 'pc4-final-release-v1', 'finalSha': 'a' * 40,
            'fixtureSha256': 'b' * 64, 'manifestSha256': 'c' * 64,
            'frontendSourceFingerprint': 'd' * 64, 'frontendOutputFingerprint': 'e' * 64,
            'targetUrl': 'http://127.0.0.1:18105', 'apiBase': 'same-origin',
            'integratedComponents': dict(CallReview=True, WmsScene=True, TmsScene=True),
            'capabilities': {'selectors': {key: '#actual-' + key for key in REQUIRED_SELECTORS}},
            'assets': [dict(path=f'demo/{case}.wav', kind='audio', caseId=case,
                            sha256='f' * 64, bytes=100, synthetic=True)
                       for case in ('CASE-0001', 'CASE-0002')]
                      + [dict(path='demo/registered.mp4', kind='video', caseId='CASE-0002',
                              sha256='f' * 64, bytes=200, synthetic=True)]}


def valid_results():
    identity = {'runNonce': 'a' * 32, 'finalSha': 'b' * 40, 'buildFingerprint': 'c' * 64}
    return ({'sameSource': True, 'sameBuild': True, 'sameTester': True, 'originalStatePreserved': True,
             'apiStopped': True, 'paidAnalyzerInvocations': 0, 'blockedExternalConnections': [],
             'browserExitCode': 0, 'identity': identity},
            {'status': 'PASS', 'guard': dict(identity, ready=True, paidAnalyzerInvocations=0, externalConnectionsBlocked=0),
             'flows': [{'caseId': case, 'repetition': repeat, 'status': 'PASS', 'store': {'store': f'{case}-{repeat}'},
                        'audio': {'judgement': {'accepted': True}}}
                       for case in ('CASE-0001', 'CASE-0002') for repeat in (1, 2, 3)],
             'plannedBoundaryIds': sorted(BOUNDARY_IDS),
             'boundaries': [{'id': key, 'status': 'PASS'} for key in sorted(BOUNDARY_IDS)], 'consoleErrors': []})


class ContractControls(unittest.TestCase):
    def test_positive_shape_is_ready_not_product_pass(self):
        self.assertEqual(required_inputs(valid_contract()), [])
    def test_missing_final_sha(self):
        d = valid_contract(); d['finalSha'] = None
        self.assertIn('FINAL_INTEGRATION_SHA_REQUIRED', required_inputs(d))
    def test_branch_is_not_immutable_sha(self):
        d = valid_contract(); d['finalSha'] = 'main'
        self.assertTrue(required_inputs(d))
    def test_missing_build_fingerprint(self):
        d = valid_contract(); d['frontendOutputFingerprint'] = None
        self.assertTrue(required_inputs(d))
    def test_old_module_declaration_rejected(self):
        d = valid_contract(); d['integratedComponents']['TmsScene'] = False
        self.assertIn('FINAL_MODULE_INTEGRATION_REQUIRED', required_inputs(d))
    def test_unresolved_actual_control(self):
        d = valid_contract(); d['capabilities']['selectors']['naturalCompletionControl'] = None
        self.assertTrue(required_inputs(d))
    def test_missing_segment_tote_or_actual_tms_selector(self):
        for key in ('segmentControl', 'differentToteNotice', 'tmsRegion', 'tmsRawSourceControl'):
            with self.subTest(selector=key):
                d = valid_contract(); del d['capabilities']['selectors'][key]
                self.assertIn('REAL_UI_SELECTOR_REQUIRED:' + key, required_inputs(d))
    def test_external_and_ambiguous_origins_rejected(self):
        for url in ('https://github.com', 'http://127.0.0.1.evil:18105', 'http://user@127.0.0.1:18105', 'http://127.0.0.1:18105/path'):
            with self.subTest(url=url):
                d = valid_contract(); d['targetUrl'] = url
                self.assertIn('ISOLATED_LOOPBACK_ORIGIN_REQUIRED', required_inputs(d))
    def test_path_traversal_rejected(self):
        for name in ('../a', '/demo/a', 'demo/../a', 'demo\\a', 'demo/%2e%2e/a', 'C:/a'):
            self.assertFalse(safe_name(name), name)
    def test_asset_duplicate_rejected(self):
        d = valid_contract(); d['assets'].append(copy.deepcopy(d['assets'][0]))
        self.assertTrue(required_inputs(d))
    def test_missing_case_audio_rejected(self):
        d = valid_contract(); d['assets'].pop(0)
        self.assertTrue(required_inputs(d))
    def test_missing_video_not_assumed_available(self):
        d = valid_contract(); d['assets'].pop()
        self.assertTrue(required_inputs(d))
    def test_non_synthetic_rejected(self):
        d = valid_contract(); d['assets'][0]['synthetic'] = False
        self.assertTrue(required_inputs(d))
    def test_gate_positive_control(self):
        self.assertEqual(aggregate_guard(*valid_results()), [])
    def test_guard_drift_always_fails_even_browser_zero(self):
        for name in ('sameSource', 'sameBuild', 'sameTester', 'originalStatePreserved', 'apiStopped'):
            with self.subTest(name=name):
                r, b = valid_results(); r[name] = False
                self.assertIn(name, aggregate_guard(r, b))
    def test_missing_guard_is_not_success(self):
        r, b = valid_results(); del r['sameSource']
        self.assertTrue(aggregate_guard(r, b))
    def test_partial_six_fails(self):
        r, b = valid_results(); b['flows'].pop()
        self.assertTrue(aggregate_guard(r, b))
    def test_wrong_case_count_fails(self):
        r, b = valid_results(); b['flows'][0]['caseId'] = 'CASE-0002'
        self.assertTrue(aggregate_guard(r, b))
    def test_skipped_boundary_fails(self):
        r, b = valid_results(); b['boundaries'][0]['status'] = 'NOT_RUN'
        self.assertTrue(aggregate_guard(r, b))
    def test_no_boundaries_fails(self):
        r, b = valid_results(); b['boundaries'] = []
        self.assertTrue(aggregate_guard(r, b))
    def test_no_browser_evidence_fails(self):
        r, b = valid_results(); self.assertTrue(aggregate_guard(r, None))
    def test_paid_attempt_fails(self):
        r, b = valid_results(); r['paidAnalyzerInvocations'] = 1
        self.assertTrue(aggregate_guard(r, b))
    def test_external_request_fails(self):
        r, b = valid_results(); b['blockedExternal'] = ['test-only.invalid']
        self.assertTrue(aggregate_guard(r, b))
    def test_setup_error_fails(self):
        r, b = valid_results(); b['setupErrors'] = ['fixture unavailable']
        self.assertTrue(aggregate_guard(r, b))
    def test_page_error_fails(self):
        r, b = valid_results(); b['consoleErrors'] = [{'kind': 'pageerror'}]
        self.assertTrue(aggregate_guard(r, b))
    def test_duplicate_repetition_fails(self):
        r, b = valid_results(); b['flows'][0]['repetition'] = 2
        self.assertTrue(aggregate_guard(r, b))
    def test_reused_store_fails(self):
        r, b = valid_results(); b['flows'][0]['store'] = b['flows'][1]['store']
        self.assertTrue(aggregate_guard(r, b))
    def test_missing_natural_audio_fails(self):
        r, b = valid_results(); del b['flows'][0]['audio']
        self.assertTrue(aggregate_guard(r, b))
    def test_blocked_status_fails_even_counts_pass(self):
        r, b = valid_results(); b['status'] = 'NOT_RUN'
        self.assertTrue(aggregate_guard(r, b))
    def test_missing_server_identity_fails(self):
        r, b = valid_results(); del b['guard']
        self.assertTrue(aggregate_guard(r, b))
    def test_wrong_nonce_fails(self):
        r, b = valid_results(); b['guard']['runNonce'] = 'other-run'
        self.assertTrue(aggregate_guard(r, b))
    def test_missing_required_boundary_fails(self):
        r, b = valid_results(); b['boundaries'].pop()
        self.assertTrue(aggregate_guard(r, b))
    def test_duplicate_boundary_cannot_cover_missing(self):
        r, b = valid_results(); b['boundaries'][0] = copy.deepcopy(b['boundaries'][1])
        self.assertTrue(aggregate_guard(r, b))
    def test_build_provenance_positive(self):
        h = {'data/overlays/pc4-tms.json': 'current'}
        record = dict(status='complete', buildExitCode=0, headBefore='final', headAfter='final',
                      productBefore=h, productAfter=h, outputFingerprint='out', nextPublicApiBase='')
        self.assertEqual(build_provenance_errors(record, 'final', h, 'out'), [])
    def test_old_overlay_build_rejected(self):
        h = {'data/overlays/pc4-tms.json': 'current'}
        old = {'data/overlays/pc4-tms.json': 'old'}
        record = dict(status='complete', buildExitCode=0, headBefore='final', headAfter='final',
                      productBefore=old, productAfter=old, outputFingerprint='out', nextPublicApiBase='')
        self.assertIn('BUILD_PRODUCT_INPUT_MISMATCH', build_provenance_errors(record, 'final', h, 'out'))
    def test_build_from_old_head_rejected(self):
        h = {'file': 'hash'}
        record = dict(status='complete', buildExitCode=0, headBefore='old', headAfter='old',
                      productBefore=h, productAfter=h, outputFingerprint='out', nextPublicApiBase='')
        self.assertIn('BUILD_NOT_FROM_FINAL_SHA', build_provenance_errors(record, 'final', h, 'out'))
    def test_old_build_output_rejected(self):
        h = {'file': 'hash'}
        record = dict(status='complete', buildExitCode=0, headBefore='final', headAfter='final',
                      productBefore=h, productAfter=h, outputFingerprint='old-out', nextPublicApiBase='')
        self.assertIn('BUILD_OUTPUT_OR_ORIGIN_MISMATCH', build_provenance_errors(record, 'final', h, 'out'))


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContractControls)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({'kind': 'checker-only-mutation-controls', 'executed': result.testsRun,
                      'passed': result.testsRun - len(result.failures) - len(result.errors),
                      'failed': len(result.failures) + len(result.errors), 'productExecutions': 0}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
