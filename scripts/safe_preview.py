"""Render a deliberately small, static SVG subset; never fetch resources.

This is a separate opt-in preview gate, not a general HTML/SVG sanitizer.
"""
import argparse
import re
from pathlib import Path
import xml.etree.ElementTree as ET

MAX_BYTES = 65536
MAX_ELEMENTS = 256
MAX_DEPTH = 12
NS = 'http://www.w3.org/2000/svg'
NUM = r'-?(?:\d{1,5}(?:\.\d{1,3})?|\.\d{1,3})'
COMMON = {'fill', 'stroke', 'stroke-width', 'opacity'}
ATTRS = {
    'svg': {'viewBox', 'width', 'height', 'role', 'aria-label'},
    'g': set(), 'title': set(), 'desc': set(),
    'rect': {'x', 'y', 'width', 'height', 'rx'},
    'line': {'x1', 'y1', 'x2', 'y2'},
    'circle': {'cx', 'cy', 'r'},
    'text': {'x', 'y', 'font-size', 'text-anchor'},
}

def preview(source: bytes) -> str:
    if len(source) > MAX_BYTES:
        raise ValueError('SVG exceeds 64 KiB')
    text = source.decode('utf-8', errors='strict')
    # Refuse XML declarations, DTDs, entities, processing instructions/comments.
    # Never expand entity declarations, even when hidden before the SVG root.
    if '<!' in text or '<?' in text:
        raise ValueError('XML declarations and processing instructions are not allowed')
    root = ET.fromstring(text)
    if root.tag != '{' + NS + '}svg':
        raise ValueError('expected SVG namespace root')
    count = 0
    def validate(node, depth):
        nonlocal count
        count += 1
        if count > MAX_ELEMENTS or depth > MAX_DEPTH:
            raise ValueError('SVG element/depth limit exceeded')
        tag = node.tag.removeprefix('{' + NS + '}')
        if node.tag != '{' + NS + '}' + tag or tag not in ATTRS:
            raise ValueError('unsupported element')
        if tag == 'svg' and depth != 0:
            raise ValueError('nested SVG not supported')
        for key, value in node.attrib.items():
            if key not in ATTRS[tag] | COMMON:
                raise ValueError('unsupported attribute: ' + key)
            if key in {'fill', 'stroke'}:
                valid = value == 'none' or re.fullmatch(r'#[0-9a-fA-F]{6}', value)
            elif key == 'viewBox':
                valid = re.fullmatch(rf'{NUM} {NUM} {NUM} {NUM}', value)
                if valid:
                    valid = all(float(n) > 0 for n in value.split()[2:])
            elif key in {'role', 'text-anchor'}:
                valid = value in ({'img'} if key == 'role' else {'start','middle','end'})
            elif key == 'aria-label':
                valid = 0 < len(value) <= 300
            else:
                valid = re.fullmatch(NUM, value)
                if valid:
                    valid = abs(float(value)) <= 10000
                if valid and key in {'width','height','rx','r','font-size','stroke-width','opacity'}:
                    valid = float(value) >= 0
                if valid and key == 'opacity':
                    valid = float(value) <= 1
            if not valid:
                raise ValueError('unsupported value for ' + key)
        for child in node:
            validate(child, depth + 1)
    validate(root, 0)
    if not root.get('viewBox') or root.find('{' + NS + '}title') is None:
        raise ValueError('viewBox and title required')
    ET.register_namespace('', NS)
    # Serialized text is escaped by ElementTree. No arbitrary HTML is carried.
    svg = ET.tostring(root, encoding='unicode')
    return ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; '
            'base-uri &#39;none&#39;; form-action &#39;none&#39;">'
            '<title>Prévia sintética</title></head><body>' + svg + '</body></html>\n')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error('output must differ from input')
    try:
        with args.source.open('rb') as handle:
            result = preview(handle.read(MAX_BYTES + 1))
        # Never silently overwrite an existing artifact.
        with args.output.open('x', encoding='utf-8') as handle:
            handle.write(result)
    except (OSError, ValueError, ET.ParseError) as exc:
        parser.exit(1, f'preview refused: {exc}\n')

if __name__ == '__main__':
    main()
