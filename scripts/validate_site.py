"""Validate the static site and optionally create an allowlisted Pages artifact."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import argparse
import re
import shutil
import struct

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Site(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.anchors = []
        self.assets = set()
        self.images = []
        self.talks = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            self.ids.append(a['id'])
        if tag == 'a':
            self.anchors.append(a)
        if tag == 'img' and a.get('src'):
            require(a.get('alt'), 'Image alt text is required')
            require(a.get('width') and a.get('height'), 'Declare intrinsic image dimensions')
            self.images.append(a['src'])
        if tag == 'button' and 'talk-photo' in a.get('class', '').split():
            self.talks.append(a['data-full'])
        for key in ('src', 'data-full'):
            if a.get(key):
                self.assets.add(a[key])
        if tag == 'link' and a.get('rel') == 'stylesheet' and not a['href'].startswith('https://'):
            self.assets.add(a['href'])


def publication_source(relative, *, allow_root_files=False):
    parts = relative.split('/')
    root_file = allow_root_files and relative in {'index.html', '.nojekyll'}
    # Accept canonical, portable relative URL paths only; never normalize them.
    if (not root_file and (len(parts) < 2 or parts[0] != 'assets')) or any(
        part in {'', '.', '..'}
        or part.endswith((' ', '.'))
        or re.search(r'[\\<>:"|?*%#\x00-\x1f\x7f]', part)
        or re.fullmatch(r'(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?: *\..*)?', part, re.I)
        for part in parts
    ):
        raise ValueError(f'Invalid publication path: {relative}')
    source = ROOT.joinpath(*parts)
    current = ROOT
    for part in parts:
        current = current / part
        if current.is_symlink() or getattr(current, 'is_junction', lambda: False)():
            raise ValueError(f'Missing or unsafe publication file: {relative}')
    boundary = ROOT.resolve() if root_file else (ROOT / 'assets').resolve()
    if not source.resolve().is_relative_to(boundary):
        raise ValueError(f'Invalid publication path: {relative}')
    if not source.is_file():
        raise ValueError(f'Missing or unsafe publication file: {relative}')
    return source


def validate():
    html = publication_source('index.html', allow_root_files=True).read_text(encoding='utf-8')
    publication_source('.nojekyll', allow_root_files=True)
    p = Site()
    p.feed(html)
    require(not [k for k, n in Counter(p.ids).items() if n > 1], 'Duplicate element IDs')
    for anchor in p.anchors:
        href = anchor['href']
        if href.startswith('#'):
            require(href[1:] in p.ids, f'Broken section link: {href}')
        elif href.startswith('https://'):
            if anchor.get('target') == '_blank':
                require('noopener' in anchor.get('rel', '').split(), 'External link needs noopener')
        else:
            require(re.fullmatch(r'tel:\+[0-9]+', href), 'Only HTTPS and valid telephone links are permitted')
    for asset in p.assets:
        publication_source(asset)
    expected = {
        'https://lin.ee/Wjt5Hny', 'https://www.youtube.com/@kenkao0127',
        'https://maps.app.goo.gl/tgkNG9uiXQB17oSY9', 'https://lin.ee/j3BF0Tz',
        'https://maps.app.goo.gl/L5pGWgFMGXgheZHG8', 'https://lin.ee/Q2s1RMM',
        'tel:+8866' + '3039028', 'tel:+8866' + '2215289',
    }
    require(expected.issubset({a['href'] for a in p.anchors}), 'Missing confirmed contact links')
    require(len(p.talks) == 7 and len(set(p.talks)) == 7, 'Expected seven distinct talk photos')
    require(len(set(p.images)) == 10, 'Expected two portraits, seven talks, and one QR code')
    background = re.search(r'<section[^>]+id="background".*?</section>', html, re.S).group()
    beyond = re.search(r'<section[^>]+id="beyond".*?</section>', html, re.S).group()
    require('background-portrait.png' not in background, 'Portrait must not be in the background section')
    require('background-portrait.png' in beyond, 'Portrait must remain in the beyond section')
    data = publication_source('assets/images/line-qr.png').read_bytes()
    require(data[:8] == b'\x89PNG\r\n\x1a\n', 'LINE QR bitmap must be PNG')
    width, height = struct.unpack('>II', data[16:24])
    require(width == height, 'LINE QR bitmap must remain square')
    print(f'PASS: {len(p.ids)} IDs; {len(p.assets)} local assets; 7 talks; confirmed clinic links; portrait location; square QR')
    return {'index.html', '.nojekyll', *p.assets}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', type=Path)
    args = parser.parse_args()
    files = validate()
    if args.build:
        require(
            not args.build.is_symlink() and not getattr(args.build, 'is_junction', lambda: False)(),
            'Build into a fresh directory',
        )
        target = args.build.resolve()
        require(not target.exists(), 'Build into a fresh directory')
        require(not target.is_relative_to((ROOT / 'assets').resolve()), 'Do not overwrite source assets')
        target.mkdir(parents=True)
        for rel in sorted(files):
            source = publication_source(rel, allow_root_files=True)
            destination = target / rel
            require(destination.resolve().is_relative_to(target), f'Invalid publication destination: {rel}')
            for current in (destination, *destination.parents):
                require(
                    not current.is_symlink() and not getattr(current, 'is_junction', lambda: False)(),
                    f'Unsafe publication destination: {rel}',
                )
                if current == target:
                    break
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        print(f'PASS: allowlisted Pages artifact contains {len(files)} files')


if __name__ == '__main__':
    main()
