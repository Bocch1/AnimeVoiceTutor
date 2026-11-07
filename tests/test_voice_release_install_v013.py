"""Safe release listing, pinned-source extraction, and declarative overlay tests."""
from __future__ import annotations
import hashlib,io,json,zipfile
from pathlib import Path
import pytest
from tools.github_character_release import get_owner_repo,public_assets,verified_release_asset,download
from tools.fetch_pinned_engine import extract_pinned
from tools.apply_engine_overlay import apply

COMMIT='04a44eb977586645f33594b72af13a035a2056c6'

def test_release_discovery_filters_non_public_and_unrelated_assets():
    url='https://github.com/example/AnimeVoiceTutor/releases'
    def source(u):
        assert u=='https://api.github.com/repos/example/AnimeVoiceTutor/releases?per_page=100'
        def asset(name, id):
            return {'id':id,'name':name,'state':'uploaded','size':10,'digest':'',
                    'browser_download_url':f'https://github.com/example/AnimeVoiceTutor/releases/download/v1/{name}'}
        return [
            {'draft':True,'assets':[asset('AnimeVoiceTutor_Character_NotPublic.zip',1)]},
            {'prerelease':False,'draft':False,'tag_name':'v1','assets':[asset('AnimeVoiceTutor_Character_Test.zip',2),asset('SomeOther.zip',3)]}
        ]
    assert get_owner_repo(url)==('example','AnimeVoiceTutor')
    assert [a['id'] for a in public_assets(url,source)]==[2]
    with pytest.raises(ValueError):get_owner_repo('http://github.com/example/x/releases')
    with pytest.raises(ValueError):get_owner_repo('https://evil.example/x/releases')


def test_download_checks_size_and_sha_before_rename(tmp_path):
    blob=b'sample-pack'
    sha=hashlib.sha256(blob).hexdigest()
    data={'id':5,'name':'AnimeVoiceTutor_Character_Test.zip','state':'uploaded','size':len(blob),'digest':'sha256:'+sha,
          'browser_download_url':'https://github.com/example/AnimeVoiceTutor/releases/download/v1/AnimeVoiceTutor_Character_Test.zip'}
    class Download(io.BytesIO):
        def __enter__(self):return self
        def __exit__(self,*args):self.close()
    path=download(data,tmp_path,lambda url:Download(blob))
    assert path.read_bytes()==blob
    data['digest']='sha256:'+'0'*64
    with pytest.raises(ValueError):download(data,tmp_path/'bad',lambda url:Download(blob))
    assert not list((tmp_path/'bad').glob('*.zip'))


def test_pinned_engine_archive_and_traversal(tmp_path):
    archive=tmp_path/'src.zip'
    base='GPT-SoVITS-'+COMMIT+'/'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr(base+'api_v2.py','print(123)')
        z.writestr(base+'GPT_SoVITS/TTS_infer_pack/TTS.py','x')
    extract_pinned(archive,tmp_path/'engine',COMMIT)
    assert (tmp_path/'engine'/'api_v2.py').exists()
    assert json.loads((tmp_path/'engine'/'.avt_engine_source.json').read_text())['commit']==COMMIT
    with pytest.raises(FileExistsError):extract_pinned(archive,tmp_path/'engine',COMMIT)
    bad=tmp_path/'bad.zip'
    with zipfile.ZipFile(bad,'w') as z:
        z.writestr(base+'api_v2.py','ok')
        z.writestr(base+'../bad.py','bad')
    with pytest.raises(ValueError):extract_pinned(bad,tmp_path/'broken',COMMIT)


def test_overlay_preview_apply_backup_and_hashes(tmp_path):
    engine=tmp_path/'engine';(engine/'GPT_SoVITS').mkdir(parents=True)
    (engine/'api_v2.py').write_bytes(b'api')
    old=b'before';new=b'after'
    target=engine/'GPT_SoVITS/TTS.py';target.write_bytes(old)
    zip_path=tmp_path/'overlay.zip'
    manifest={'schema_version':1,'type':'avt-engine-overlay','files':[{'path':'GPT_SoVITS/TTS.py',
          'before_sha256':hashlib.sha256(old).hexdigest(),'after_sha256':hashlib.sha256(new).hexdigest()}]}
    with zipfile.ZipFile(zip_path,'w') as z:
        z.writestr('engine_overlay.json',json.dumps(manifest))
        z.writestr('payload/GPT_SoVITS/TTS.py',new)
    assert apply(zip_path,engine,dry_run=True)==['GPT_SoVITS/TTS.py']
    assert target.read_bytes()==old
    assert apply(zip_path,engine)==['GPT_SoVITS/TTS.py']
    assert target.read_bytes()==new
    assert list((tmp_path/'engine_avt_overlay_backup').rglob('TTS.py'))
    with pytest.raises(ValueError):apply(zip_path,engine)
    manifest['files'][0]['path']='../outside.py'
    with zipfile.ZipFile(zip_path,'w') as z:
        z.writestr('engine_overlay.json',json.dumps(manifest))
        z.writestr('payload/../outside.py',new)
    with pytest.raises(ValueError):apply(zip_path,engine)
