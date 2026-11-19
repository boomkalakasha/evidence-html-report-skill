import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from test_builder import builder, ROOT


class NativeReportTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'examples/shared-architecture.json').read_text(encoding='utf8'))
        self.data['readingMode'] = 'continuous'  # This fixture exercises the legacy reader.
        self.data['sections'][1]['figure']['src'] = str(ROOT / 'examples/assets/architecture.svg')

    def render(self, data, strict=False):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp)/'in.json', Path(tmp)/'out.html'
            source.write_text(json.dumps(data, ensure_ascii=False), encoding='utf8')
            builder.build(source, output, strict=strict)
            return output.read_text(encoding='utf8')

    def test_native_assets_are_embedded_and_source_conclusion_precedes_metadata(self):
        output = self.render(self.data, strict=True)
        self.assertIn('data:image/svg+xml;base64,', output)
        self.assertLess(output.index('<section class="verdict"'), output.index('<div class="report-meta"'))
        for scenario in self.data['scenarios']:
            self.assertIn('data-scenario="'+scenario['id']+'"', output)
        self.assertIn('未来方案，尚不可作为可运行能力', output)

    def test_missing_component_and_bad_edge_fail(self):
        bad = copy.deepcopy(self.data); bad['graphs'][0]['nodes'][0]['component'] = 'absent'
        with self.assertRaises(ValueError): self.render(bad)
        bad = copy.deepcopy(self.data); bad['graphs'][0]['edges'][0]['to'] = 'absent'
        with self.assertRaises(ValueError): self.render(bad)

    def test_trace_must_belong_to_its_selected_graph(self):
        self.data['scenarios'][0]['steps'][0]['node'] = 'not-in-graph'
        with self.assertRaises(ValueError): self.render(self.data)

    def test_unregistered_scenario_is_rejected(self):
        self.data['sections'][0]['scenarioIds'].append('not-registered')
        with self.assertRaises(ValueError): self.render(self.data)

    def test_unknown_fields_warn_by_default_and_fail_strict(self):
        self.data['sections'][2]['imaginaryFigure'] = 'must-not-silently-disappear'
        err = io.StringIO()
        with contextlib.redirect_stderr(err): self.render(self.data)
        self.assertIn('imaginaryFigure', err.getvalue())
        with self.assertRaises(ValueError): self.render(self.data, strict=True)

    def test_native_data_still_uses_registered_evidence(self):
        self.data['components'][0]['evidence'] = ['missing']
        with self.assertRaises(ValueError): self.render(self.data)

    def test_invalid_input_preserves_previous_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp)/'in.json', Path(tmp)/'out.html'
            output.write_text('previous', encoding='utf8')
            self.data['sections'][1]['figure']['src'] = 'absent.svg'
            source.write_text(json.dumps(self.data), encoding='utf8')
            with self.assertRaises(ValueError): builder.build(source, output)
            self.assertEqual(output.read_text(encoding='utf8'), 'previous')

    def test_new_controls_cannot_collide_with_user_chapters(self):
        self.data['sections'][0]['id'] = 'chapter-dialog'
        with self.assertRaises(ValueError): self.render(self.data)
