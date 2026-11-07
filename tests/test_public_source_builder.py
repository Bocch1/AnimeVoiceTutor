"""Regressions for self-contained releases from the canonical source root."""
from pathlib import Path
import re
from tools.build_public_source import public_paths, check_text_privacy, SECRET_PATTERNS

ROOT = Path(__file__).resolve().parents[1]

def test_public_export_manifest_is_valid():
    paths = public_paths(ROOT)
    assert paths == sorted(paths)
    assert 'Build Public Source.cmd' in paths
    assert '.env.example' in paths
    assert 'release/public_source_files.txt' in paths
    assert 'tools/build_public_source.py' in paths

def test_public_export_does_not_require_developer_installation():
    paths = public_paths(ROOT)
    assert not any(name.startswith(('data/', 'models/', 'external/', 'runtime/', 'backups/')) for name in paths)

def test_public_text_contains_no_known_machine_paths_or_keys():
    check_text_privacy(ROOT, public_paths(ROOT))

def test_private_patterns_reject_realistic_credentials_and_home_paths():
    probes = ['DEEPSEEK_API_KEY=sk-' + 'a'*30, 'C:' + chr(92) + 'Users' + chr(92) + 'SomeUser' + chr(92) + 'Desktop']
    assert all(any(regex.search(candidate) for regex in SECRET_PATTERNS) for candidate in probes)
