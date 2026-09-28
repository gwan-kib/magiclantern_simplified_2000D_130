import json
import unittest

from tools.eos2000d.feature_matrix import validate as validate_features
from tools.eos2000d.memory_report import analyze as analyze_memory
from tools.eos2000d.stub_evidence import active_stubs, validate as validate_stubs


class StubEvidenceTests(unittest.TestCase):
    def test_empty_stub_file_is_valid_with_empty_evidence(self):
        self.assertEqual(validate_stubs("/* none */", {"stubs": []}), [])

    def test_active_stub_requires_hash_and_evidence(self):
        text = "NSTUB(0x1234, msleep)\n"
        errors = validate_stubs(text, {"stubs": [{"symbol": "msleep", "address": "0x1234", "status": "rom-verified", "evidence": []}]})
        self.assertTrue(any("ROM SHA-256" in error for error in errors))
        self.assertTrue(any("evidence list" in error for error in errors))

    def test_comment_stub_is_not_active(self):
        self.assertEqual(active_stubs("// NSTUB(0x1234, msleep)"), {})


class FeatureMatrixTests(unittest.TestCase):
    def test_disabled_port_with_matrix_passes(self):
        matrix = {"features": [{"name": "FEATURE_HISTOGRAM", "status": "Disabled", "evidence": []}], "modules": []}
        self.assertEqual(validate_features("#ifndef X\n#endif\n", "", matrix), [])

    def test_enabled_feature_requires_evidence(self):
        matrix = {"features": [{"name": "FEATURE_HISTOGRAM", "status": "Compiles", "evidence": []}], "modules": []}
        errors = validate_features("#define FEATURE_HISTOGRAM\n", "", matrix)
        self.assertTrue(any("without supporting evidence" in error for error in errors))

    def test_all_features_bundle_is_rejected(self):
        errors = validate_features('#include "all_features.h"\n', "", {"features": [], "modules": []})
        self.assertTrue(any("all_features.h" in error for error in errors))


class MemoryReportTests(unittest.TestCase):
    def test_overlap_and_canary_are_detected(self):
        records = [{
            "ml_region": {"start": 100, "end": 200},
            "canon_regions": [{"name": "heap", "start": 150, "end": 250}],
            "canary_ok": False,
            "free_memory": 1000
        }]
        errors = analyze_memory(records)
        self.assertTrue(any("overlaps" in error for error in errors))
        self.assertTrue(any("canary" in error for error in errors))

    def test_stable_records_pass_with_tolerance(self):
        records = [
            {"free_memory": 1000, "canary_ok": True},
            {"free_memory": 995, "canary_ok": True}
        ]
        self.assertEqual(analyze_memory(records, drift_limit=5), [])


if __name__ == "__main__":
    unittest.main()
