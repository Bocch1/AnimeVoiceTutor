"""Discover public GitHub Release character ZIPs and download a selected asset.

The app never executes downloaded ZIP contents. The existing character importer
validates the archive before activation. Users must trust the repository.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

MAX_BYTES = 4 * 1024**3
CHUNK = 1024 * 1024
ASSET_NAME = re.compile(r'^AnimeVoiceTutor_Character_[A-Za-z0-9_.-]+\.zip$', re.I)
RELEASE_URL = re.compile(r'^https://github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+)/releases/?$')


def get_owner_repo(url: str) -> tuple[str, str]:
    match = RELEASE_URL.fullmatch(url.strip())
    if not match:
        raise ValueError('Enter an HTTPS GitHub repository Releases URL')
    return match.group(1), match.group(2)


def verified_release_asset(asset: dict) -> dict:
    name = str(asset.get('name', ''))
    url = str(asset.get('browser_download_url', ''))
    if not ASSET_NAME.fullmatch(name) or asset.get('state') != 'uploaded':
        raise ValueError('Not a published AnimeVoiceTutor character archive')
    if not re.fullmatch(r'https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/releases/download/[^/\s]+/[A-Za-z0-9_.-]+\.zip',url):
        raise ValueError('Invalid GitHub release asset URL')
    if not url.endswith('/'+name):
        raise ValueError('Asset name does not match URL')
    size = int(asset.get('size', 0))
    if size <= 0 or size > MAX_BYTES:
        raise ValueError('Invalid character asset size')
    digest = str(asset.get('digest') or '')
    if digest and not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', digest):
        raise ValueError('Unexpected asset checksum format')
    return {'id':int(asset['id']),'name':name,'url':url,'size':size,'digest':digest.lower()}


def public_assets(releases_url: str, fetch=None) -> list[dict]:
    owner,repo = get_owner_repo(releases_url)
    api = f'https://api.github.com/repos/{owner}/{repo}/releases?per_page=100'
    if fetch is None:
        def fetch(url):
            req = Request(url,headers={'User-Agent':'AnimeVoiceTutor-Installer/0.13.1','Accept':'application/vnd.github+json'})
            with urlopen(req, timeout=30) as response:
                return json.load(response)
    releases = fetch(api)
    if not isinstance(releases,list):
        raise ValueError('Unexpected GitHub Releases response')
    found=[]
    for release in releases:
        if release.get('draft') or release.get('prerelease'):
            continue
        for asset in release.get('assets',[]):
            try:
                item=verified_release_asset(asset)
                # Reject asset from unrelated repository even if name looks correct.
                if not item['url'].startswith(f'https://github.com/{owner}/{repo}/releases/download/'):
                    continue
                item['release']=str(release.get('tag_name',''))
                found.append(item)
            except (KeyError,TypeError,ValueError):
                continue
    return found


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(CHUNK), b''):
            digest.update(chunk)
    return digest.hexdigest()


def download(asset: dict, dest: Path, stream_open=None) -> Path:
    checked=verified_release_asset(asset)
    dest=dest.resolve()
    dest.mkdir(parents=True,exist_ok=True)
    target=dest/checked['name']
    if target.exists():
        # Safe repeat installations should reuse an already verified download.
        if target.stat().st_size != checked['size']:
            raise FileExistsError(f'Download destination has a different size: {target}')
        if checked['digest'] and 'sha256:' + _file_sha256(target) != checked['digest']:
            raise FileExistsError(f'Existing character ZIP SHA-256 mismatch: {target}')
        return target
    part=dest/(checked['name']+'.part')
    if part.exists():
        raise FileExistsError(f'Partial download already exists: {part}')
    if stream_open is None:
        def stream_open(url):
            return urlopen(Request(url,headers={'User-Agent':'AnimeVoiceTutor-Installer/0.13.1'}),timeout=90)
    actual=hashlib.sha256();size=0
    try:
        with stream_open(checked['url']) as response,part.open('xb') as out:
            while block:=response.read(CHUNK):
                size+=len(block)
                if size>MAX_BYTES or size>checked['size']:
                    raise ValueError('Character download exceeds published size')
                actual.update(block);out.write(block)
        if size!=checked['size']:
            raise ValueError('Character download size mismatch')
        if checked['digest'] and 'sha256:'+actual.hexdigest()!=checked['digest']:
            raise ValueError('Character download SHA-256 mismatch')
        part.rename(target)
    finally:
        if part.exists():part.unlink()
    return target


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--releases-url',required=True)
    parser.add_argument('--list',action='store_true')
    parser.add_argument('--asset-id',type=int)
    parser.add_argument('--download-dir',type=Path)
    parser.add_argument('--install-and-select',action='store_true')
    args=parser.parse_args()
    assets=public_assets(args.releases_url)
    if args.list:
        print(json.dumps(assets,ensure_ascii=False));return
    matching=[a for a in assets if a['id']==args.asset_id]
    if len(matching)!=1 or args.download_dir is None:
        raise ValueError('Select a valid published character asset ID and download directory')
    path=download(matching[0],args.download_dir)
    print('DOWNLOADED_CHARACTER_ZIP:',path)
    if args.install_and_select:
        sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
        from tools.install_and_select_character import install_once
        from voice_tutor.characters import select_character
        result=install_once(path)
        select_character(result['id'])
        print('CHARACTER_DOWNLOADED_INSTALLED_SELECTED:',result['id'])

if __name__=='__main__':
    main()
