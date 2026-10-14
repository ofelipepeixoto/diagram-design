import importlib.util
from pathlib import Path
import unittest
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location('safe_preview', Path(__file__).with_name('safe_preview.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
def svg(body='', attrs=''):
    return f'<svg xmlns="{m.NS}" viewBox="0 0 100 100" {attrs}><title>Fixture</title>{body}</svg>'.encode()

class PreviewTests(unittest.TestCase):
    def test_synthetic_diagram(self):
        source = Path(__file__).parents[1] / 'docs/synthetic-evidence-flow.svg'
        result = m.preview(source.read_bytes())
        self.assertIn('Content-Security-Policy', result)
        self.assertIn('Revisão humana', result)

    def test_reject_active_or_external_content(self):
        for body in ['<script/>', '<foreignObject/>', '<image href="https://example.invalid/a"/>',
                     '<use href="#a"/>', '<style/>', '<a href="file:///tmp/a"/>',
                     '<rect style="fill:url(https://example.invalid)"/>',
                     '<rect fill="url(#a)"/>', '<rect onload="noop"/>',
                     '<rect xmlns="urn:other"/>', '<svg/>']:
            with self.subTest(body=body), self.assertRaises(ValueError):
                m.preview(svg(body))

    def test_reject_resource_limits_and_entities(self):
        for source in [b'x' * (m.MAX_BYTES+1), svg('<g>'*14+'</g>'*14),
                       svg('<rect/>'*257), b'<!DOCTYPE svg [<!ENTITY a "x">]>'+svg(),
                       b'<?xml-stylesheet href="https://example.invalid"?>'+svg(),
                       svg(attrs='width="1000000000"'), svg('<rect opacity="2"/>')]:
            with self.subTest(source=source[:80]), self.assertRaises(ValueError):
                m.preview(source)

    def test_escape_text_and_no_script(self):
        out = m.preview(svg('<text x="1" y="1">&lt;script&gt; &amp; literal</text>'))
        self.assertIn('&lt;script&gt;', out)
        self.assertNotIn('<script>', out)

    def test_invalid_xml_and_missing_title(self):
        with self.assertRaises(ET.ParseError):
            m.preview(b'<svg')
        with self.assertRaises(ValueError):
            m.preview(f'<svg xmlns="{m.NS}"/>'.encode())

    def test_cli_refuses_overwrite_and_bounded_input(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'source.svg'
            output = Path(directory)/'preview.html'
            source.write_bytes(svg())
            output.write_text('keep')
            command = [sys.executable, str(Path(__file__).with_name('safe_preview.py')), str(source)]
            self.assertNotEqual(subprocess.run(command+[str(output)],capture_output=True).returncode,0)
            self.assertEqual(output.read_text(),'keep')
            self.assertNotEqual(subprocess.run(command+[str(source)],capture_output=True).returncode,0)
            output.unlink()
            source.write_bytes(b'x'*(m.MAX_BYTES+1))
            self.assertNotEqual(subprocess.run(command+[str(output)],capture_output=True).returncode,0)
            self.assertFalse(output.exists())

if __name__ == '__main__':
    unittest.main()
