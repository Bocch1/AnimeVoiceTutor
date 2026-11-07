"""Safely extract third-party inference ZIPs without accessing the network."""
from pathlib import Path
import hashlib
import json
import os
import zipfile
import pytest
from tools.install_tts_pretrained import safe_members, install


def archive(path, names):
    with zipfile.ZipFile(path,'w') as z:
        for name, contents in names.items():
            # Python on Windows normalizes backslashes when writing ZipInfo.
            z.writestr(name.replace('\\', '/'), contents)
    # Build a genuinely malformed ZIP *on disk*, preserving literal \
    # characters in both local and central directory entries. Filename bytes
    # keep the same length, so ZIP offsets and headers remain valid.
    raw = path.read_bytes()
    for name in names:
        if '\\' not in name:
            continue
        safe = name.replace('\\', '/').encode('ascii')
        bad = name.encode('ascii')
        assert len(safe) == len(bad)
        assert raw.count(safe) == 2
        raw = raw.replace(safe, bad)
    path.write_bytes(raw)


def test_pretrained_local_archive_verified_and_atomic(tmp_path):
    engine=tmp_path/'engine';engine.mkdir(); (engine/'api_v2.py').write_text('print(1)')
    src=tmp_path/'p.zip';archive(src,{'pretrained_models/v5/model.bin':b'weights'})
    digest=hashlib.sha256(src.read_bytes()).hexdigest()
    assert install(src,engine,digest)==digest
    assert (engine/'GPT_SoVITS/pretrained_models/v5/model.bin').read_bytes()==b'weights'
    receipt=json.loads((engine/'.avt_pretrained_receipt.json').read_text())
    assert receipt['verified_expected_sha256']
    with pytest.raises(FileExistsError): install(src,engine,digest)


@pytest.mark.parametrize('bad', ['../other/escape.bin','pretrained_models/../../escape.bin',
                                  'C:/bad.exe','assets/random.txt','pretrained_models\\other.bin'])
def test_pretrained_refuses_unsafe_zip(tmp_path,bad):
    engine=tmp_path/'engine';engine.mkdir();(engine/'api_v2.py').write_text('x')
    p=tmp_path/'bad.zip';archive(p,{bad:b'danger'})
    if '\\' in bad:
        with zipfile.ZipFile(p) as z:
            assert z.infolist()[0].orig_filename == bad
    with pytest.raises(ValueError):install(p,engine)
    assert not (engine/'GPT_SoVITS').exists()


def test_pretrained_refuses_wrong_hash(tmp_path):
    engine=tmp_path/'engine';engine.mkdir();(engine/'api_v2.py').write_text('x')
    p=tmp_path/'p.zip';archive(p,{'pretrained_models/a.bin':b'abc'})
    with pytest.raises(ValueError,match='SHA-256'):
        install(p,engine,'0'*64)
    assert not (engine/'GPT_SoVITS').exists()
