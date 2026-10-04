"""Regression tests for the Pages publication boundary (stdlib only)."""
from contextlib import contextmanager, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import os
import shutil
import struct
import subprocess
import sys
import unittest

from scripts import validate_site


class PublicationBoundaryTests(unittest.TestCase):
    def setUp(self):
        scratch = os.environ.get('TMPDIR')
        self.temporary = TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'repository'
        self.root.mkdir()
        self.addCleanup(patch.stopall)
        patch.object(validate_site, 'ROOT', self.root).start()
        images = ['portrait.png', 'background-portrait.png', 'line-qr.png']
        images += [f'talk-{number}.jpg' for number in range(7)]
        self.assets = {'assets/site.css', 'assets/site.js'}
        self.assets.update(f'assets/images/{name}' for name in images)
        for relative in self.assets:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'fixture asset')
        (self.root / 'assets/images/line-qr.png').write_bytes(
            b'\x89PNG\r\n\x1a\n' + b'\0' * 8 + struct.pack('>II', 10, 10)
        )
        links = [
            'https://lin.ee/Wjt5Hny', 'https://www.youtube.com/@kenkao0127',
            'https://maps.app.goo.gl/tgkNG9uiXQB17oSY9', 'https://lin.ee/j3BF0Tz',
            'https://maps.app.goo.gl/L5pGWgFMGXgheZHG8', 'https://lin.ee/Q2s1RMM',
            'tel:+8866' + '3039028', 'tel:+8866' + '2215289',
        ]
        self.html = '<link rel="stylesheet" href="assets/site.css">'
        self.html += '<script src="assets/site.js"></script>'
        self.html += ''.join(f'<a href="{href}">contact</a>' for href in links)
        self.html += '<section id="background"></section>'
        self.html += '<section id="beyond">background-portrait.png</section>'
        self.html += ''.join(
            f'<img src="assets/images/{name}" alt="fixture" width="10" height="10">'
            for name in images
        )
        self.html += ''.join(
            f'<button class="talk-photo" data-full="assets/images/talk-{number}.jpg"></button>'
            for number in range(7)
        )
        (self.root / 'index.html').write_text(self.html, encoding='utf-8')
        (self.root / '.nojekyll').write_text('', encoding='utf-8')
        (self.root / 'education').mkdir()
        (self.root / 'education/index.html').write_text('<main id="main"></main>', encoding='utf-8')
        (self.root / 'education/ldl-pomelo-story.html').write_text(
            '<img src="../assets/images/portrait.png" alt="fixture" width="10" height="10">',
            encoding='utf-8',
        )
        (self.root / 'README.md').write_text('private repository document', encoding='utf-8')

    def validate(self):
        with redirect_stdout(StringIO()):
            return validate_site.validate()

    def add_reference(self, relative):
        (self.root / 'index.html').write_text(
            self.html + f'<script src="{relative}"></script>', encoding='utf-8'
        )

    def test_parent_traversal_cannot_publish_repository_document(self):
        self.add_reference('assets/../README.md')
        with self.assertRaisesRegex(ValueError, 'Invalid publication path'):
            self.validate()

    def test_noncanonical_and_windows_ambiguous_paths_are_rejected(self):
        invalid = [
            'assets/images/../../README.md', 'assets/../assets/site.js',
            'assets/./site.js', 'assets//site.js', 'assets/',
            '/assets/site.js', str(self.root / 'assets/site.js'),
            'C:/assets/site.js', 'C:assets/site.js', '//server/share/site.js',
            r'assets\images\portrait.png', r'assets/images\portrait.png',
            r'assets/..\README.md', r'\assets\site.js',
            r'\\server\share\site.js', r'\\?\C:\assets\site.js',
            'assets/site.js:stream', 'assets/site.js.', 'assets/site.js ',
            'assets/CON', 'assets/nul.txt', 'assets/COM1.js', 'assets/LPT9.txt',
            'assets/con .js', 'assets/LPT1 .txt',
            'assets/site.js?query', 'assets/site.js#fragment',
            'assets/%2e%2e/README.md', 'assets/site\x00.js', 'assets/site\n.js',
        ]
        for relative in invalid:
            with self.subTest(relative=relative):
                self.add_reference(relative)
                with self.assertRaisesRegex(ValueError, 'Invalid publication path'):
                    self.validate()

    @contextmanager
    def symbolic_link(self, link, source):
        """Exercise real symlinks when permitted; report the Windows fallback."""
        try:
            link.symlink_to(source, target_is_directory=source.is_dir())
        except OSError as error:
            print(f'Symlink privilege unavailable; using is_symlink mock: {error}', file=sys.stderr)
            if source.is_dir():
                shutil.copytree(source, link)
            elif source.is_file():
                shutil.copyfile(source, link)
            original = Path.is_symlink
            with patch.object(Path, 'is_symlink', lambda path: path == link or original(path)):
                yield
        else:
            yield

    def test_symbolic_link_asset_file_is_rejected(self):
        link = self.root / 'assets/alias.js'
        self.add_reference('assets/alias.js')
        with self.symbolic_link(link, self.root / 'assets/site.js'):
            with self.assertRaisesRegex(ValueError, 'Missing or unsafe publication file'):
                self.validate()

    def test_symbolic_link_asset_ancestor_is_rejected(self):
        link = self.root / 'assets/alias'
        self.add_reference('assets/alias/portrait.png')
        with self.symbolic_link(link, self.root / 'assets/images'):
            with self.assertRaisesRegex(ValueError, 'Missing or unsafe publication file'):
                self.validate()

    def test_symbolic_link_assets_directory_is_rejected(self):
        source = self.root / 'stored-assets'
        (self.root / 'assets').rename(source)
        with self.symbolic_link(self.root / 'assets', source):
            with self.assertRaisesRegex(ValueError, 'Missing or unsafe publication file'):
                self.validate()

    def test_symbolic_link_root_publication_files_are_rejected(self):
        for relative in ('index.html', '.nojekyll'):
            with self.subTest(relative=relative):
                link = self.root / relative
                source = self.root / f'{relative}.original'
                link.rename(source)
                try:
                    with self.symbolic_link(link, source):
                        with self.assertRaisesRegex(ValueError, 'Missing or unsafe publication file'):
                            self.validate()
                finally:
                    link.unlink()
                    source.rename(link)

    def test_missing_publication_files_are_rejected(self):
        for relative in ('assets/site.js', 'index.html', '.nojekyll', 'education/index.html'):
            with self.subTest(relative=relative):
                path = self.root / relative
                original = path.read_bytes()
                path.unlink()
                try:
                    with self.assertRaisesRegex(ValueError, 'Missing or unsafe publication file'):
                        self.validate()
                finally:
                    path.write_bytes(original)

    def test_directory_cannot_be_published_as_file(self):
        self.add_reference('assets/images')
        with self.assertRaisesRegex(ValueError, 'Missing or unsafe publication file'):
            self.validate()

    def test_resolved_asset_cannot_leave_assets_boundary(self):
        original = Path.resolve
        asset = self.root / 'assets/site.js'
        with patch.object(
            Path, 'resolve',
            lambda path, *args, **kwargs: self.root / 'README.md' if path == asset
            else original(path, *args, **kwargs),
        ):
            with self.assertRaisesRegex(ValueError, 'Invalid publication path'):
                self.validate()

    def test_validated_file_set_is_exact_allowlist(self):
        (self.root / 'assets/unreferenced.txt').write_text('not public', encoding='utf-8')
        self.assertEqual(self.validate(), {'index.html', '.nojekyll', 'education/index.html', 'education/ldl-pomelo-story.html'} | self.assets)

    def build(self, target):
        with patch.object(sys, 'argv', ['validate_site.py', '--build', str(target)]):
            with redirect_stdout(StringIO()):
                validate_site.main()

    def test_build_revalidates_publication_paths(self):
        invalid = [
            'assets/../README.md', 'README.md', 'index.html/extra',
            str(self.root / 'README.md'), '/README.md', r'assets/images\portrait.png',
        ]
        for number, relative in enumerate(invalid):
            with self.subTest(relative=relative):
                target = Path(self.temporary.name) / f'published-{number}'
                with patch.object(validate_site, 'validate', return_value={relative}):
                    with self.assertRaisesRegex(ValueError, 'Invalid publication path'):
                        self.build(target)
                self.assertFalse((target / 'README.md').exists())

    def test_resolved_destination_cannot_leave_output_directory(self):
        target = Path(self.temporary.name) / 'published'
        escaped = Path(self.temporary.name) / 'escaped.js'
        destination = target / 'assets/site.js'
        original = Path.resolve
        with patch.object(
            Path, 'resolve',
            lambda path, *args, **kwargs: escaped if path == destination
            else original(path, *args, **kwargs),
        ):
            with self.assertRaisesRegex(ValueError, 'Invalid publication destination'):
                self.build(target)
        self.assertFalse(escaped.exists())
        self.assertFalse(destination.exists())

    def test_symbolic_link_destination_ancestor_is_rejected(self):
        target = Path(self.temporary.name) / 'published'
        original = Path.is_symlink
        # Simulate metadata changing after the fresh output directory is created.
        with patch.object(
            Path, 'is_symlink',
            lambda path: path == target / 'assets' or original(path),
        ):
            with self.assertRaisesRegex(ValueError, 'Unsafe publication destination'):
                self.build(target)
        self.assertFalse((target / 'assets/site.js').exists())

    def test_symbolic_link_destination_file_is_rejected(self):
        target = Path(self.temporary.name) / 'published'
        original = Path.is_symlink
        with patch.object(
            Path, 'is_symlink',
            lambda path: path == target / '.nojekyll' or original(path),
        ):
            with self.assertRaisesRegex(ValueError, 'Unsafe publication destination'):
                self.build(target)
        self.assertFalse((target / '.nojekyll').exists())

    def test_dangling_symbolic_link_asset_is_rejected(self):
        link = self.root / 'assets/dangling.js'
        self.add_reference('assets/dangling.js')
        with self.symbolic_link(link, self.root / 'absent.js'):
            with self.assertRaisesRegex(ValueError, 'Missing or unsafe publication file'):
                self.validate()

    def test_dangling_symbolic_link_output_is_rejected(self):
        target = Path(self.temporary.name) / 'published'
        missing = Path(self.temporary.name) / 'absent-output'
        with self.symbolic_link(target, missing):
            with self.assertRaisesRegex(ValueError, 'Build into a fresh directory'):
                self.build(target)
        self.assertFalse(missing.exists())

    def test_only_explicit_root_files_are_allowed(self):
        for relative in ('index.html', '.nojekyll'):
            with self.subTest(relative=relative):
                self.assertEqual(
                    validate_site.publication_source(relative, allow_root_files=True),
                    self.root / relative,
                )
                self.add_reference(relative)
                with self.assertRaisesRegex(ValueError, 'Invalid publication path'):
                    self.validate()
        with self.assertRaisesRegex(ValueError, 'Invalid publication path'):
            validate_site.publication_source('README.md', allow_root_files=True)

    def test_built_file_set_and_contents_are_exact(self):
        (self.root / 'assets/unreferenced.txt').write_text('not public', encoding='utf-8')
        (self.root / 'content').mkdir()
        (self.root / 'content/private.md').write_text('not public', encoding='utf-8')
        target = Path(self.temporary.name) / 'published'
        self.build(target)
        actual = {
            path.relative_to(target).as_posix()
            for path in target.rglob('*') if path.is_file()
        }
        self.assertEqual(actual, {'index.html', '.nojekyll', 'education/index.html', 'education/ldl-pomelo-story.html'} | self.assets)
        for relative in actual:
            with self.subTest(relative=relative):
                self.assertEqual((target / relative).read_bytes(), (self.root / relative).read_bytes())

    def test_real_site_cli_publishes_exact_file_set(self):
        project = Path(validate_site.__file__).resolve().parents[1]
        target = Path(self.temporary.name) / 'real-site'
        result = subprocess.run(
            [sys.executable, '-B', str(project / 'scripts/validate_site.py'), '--build', str(target)],
            cwd=project, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        expected = {
            'index.html', '.nojekyll', 'education/index.html', 'education/ldl-pomelo-story.html',
            'assets/site.css', 'assets/site.js', 'assets/images/ldl-pomelo-canva.jpg',
            'assets/images/portrait.png', 'assets/images/background-portrait.png',
            'assets/images/line-qr.png', 'assets/images/talk-2025-11-23.jpg',
            'assets/images/talk-2026-03-22-1.jpg', 'assets/images/talk-2026-03-22-2.png',
            'assets/images/talk-2026-05-24.jpg', 'assets/images/talk-2026-09-08-1.jpg',
            'assets/images/talk-2026-09-08-2.jpg', 'assets/images/talk-2026-09-08-3.jpg',
        }
        actual = {
            path.relative_to(target).as_posix()
            for path in target.rglob('*') if path.is_file()
        }
        self.assertEqual(actual, expected)
        for relative in actual:
            with self.subTest(relative=relative):
                self.assertEqual((target / relative).read_bytes(), (project / relative).read_bytes())

    def test_existing_output_is_rejected(self):
        target = Path(self.temporary.name) / 'published'
        target.mkdir()
        marker = target / 'untouched.txt'
        marker.write_text('original', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Build into a fresh directory'):
            self.build(target)
        self.assertEqual(marker.read_text(encoding='utf-8'), 'original')

    def test_output_inside_source_assets_is_rejected(self):
        target = self.root / 'assets/published'
        with self.assertRaisesRegex(ValueError, 'Do not overwrite source assets'):
            self.build(target)
        self.assertFalse(target.exists())

    def test_unsafe_link_is_rejected_under_optimization(self):
        (self.root / 'index.html').write_text(
            self.html + '<a href="http://example.com">unsafe link</a>', encoding='utf-8'
        )
        result = subprocess.run(
            [sys.executable, '-B', '-O', '-c',
             'from pathlib import Path; import sys; from scripts import validate_site; '
             'validate_site.ROOT = Path(sys.argv[1]); validate_site.validate()', str(self.root)],
            cwd=Path(validate_site.__file__).resolve().parents[1],
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('Only HTTPS and valid telephone links are permitted', result.stderr)

    def test_story_hub_links_cannot_escape_published_pages(self):
        accepted = self.html + '<a href="education/">stories</a>'
        (self.root / 'index.html').write_text(accepted, encoding='utf-8')
        self.validate()
        rejected = [
            'education/../README.md',
            'javascript:alert(1)',
            'education/%2e%2e/index.html',
            '../secrets',
            '/education/',
            'education/index.html/../../README.md',
        ]
        for href in rejected:
            with self.subTest(href=href):
                (self.root / 'index.html').write_text(
                    self.html + f'<a href="{href}">nope</a>', encoding='utf-8'
                )
                with self.assertRaisesRegex(ValueError, 'Only HTTPS and valid telephone links are permitted'):
                    self.validate()

    def test_symbolic_link_stories_page_is_rejected(self):
        link = self.root / 'education/index.html'
        source = self.root / 'education/index.original.html'
        link.rename(source)
        try:
            with self.symbolic_link(link, source):
                with self.assertRaisesRegex(ValueError, 'Missing or unsafe publication file'):
                    self.validate()
        finally:
            if link.exists() or link.is_symlink():
                link.unlink()
            source.rename(link)

    def test_real_stories_hub_is_static_and_linked(self):
        project = Path(validate_site.__file__).resolve().parents[1]
        hub = (project / 'education/index.html').read_text(encoding='utf-8')
        for href in (
            'https://kenkao0127-droid.github.io/chengmei-pneumothorax-education/',
            'https://kenkao0127-droid.github.io/chengmei-pneumothorax-education/education-story.html',
            'https://www.youtube.com/watch?v=uVR-aU10Y-s',
            'ldl-pomelo-story.html',
        ):
            self.assertIn(f'href="{href}"', hub)
        lowered = hub.lower()
        self.assertNotIn('<form', lowered)
        self.assertNotIn('<input', lowered)
        self.assertNotIn('<textarea', lowered)
        index = (project / 'index.html').read_text(encoding='utf-8')
        self.assertIn('href="education/"', index)
        story = (project / 'education/ldl-pomelo-story.html').read_text(encoding='utf-8')
        self.assertIn('href="./"', story)
        self.assertIn('href="../"', story)


if __name__ == '__main__':
    unittest.main()
