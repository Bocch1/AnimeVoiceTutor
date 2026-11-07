"""Fetch pinned upstream GPT-SoVITS source without requiring Git on consumer PCs."""
from __future__ import annotations
import argparse,hashlib,json,re,shutil,stat,tempfile,zipfile
from pathlib import Path,PurePosixPath
from urllib.request import Request,urlopen

MAX_DOWNLOAD=2*1024**3
MAX_EXPANDED=6*1024**3

def extract_pinned(archive:Path,destination:Path,commit:str) -> None:
    if not re.fullmatch('[a-f0-9]{40}',commit):
        raise ValueError('Expected full pinned SHA-1 commit')
    if destination.exists():
        raise FileExistsError('Engine destination exists; no overwrite')
    prefix='GPT-SoVITS-'+commit+'/'
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        members=source.infolist();total=0
        if len(members)>10000:raise ValueError('Excessive ZIP entries')
        for item in members:
            raw=item.orig_filename
            if (raw!=item.filename or not raw.startswith(prefix) or '\\' in raw or ':' in raw or '\x00' in raw
                or any(p in ('','..','.') for p in raw[len(prefix):].rstrip('/').split('/') if p!='')
                or ((item.external_attr>>16)&0o170000)==stat.S_IFLNK):
                raise ValueError('Unsafe GPT-SoVITS archive entry')
            total+=item.file_size
            if total>MAX_EXPANDED:raise ValueError('Engine archive expanded size limit')
        with tempfile.TemporaryDirectory(prefix='avt_engine_',dir=destination.parent) as td:
            tmp=Path(td)/'engine';tmp.mkdir()
            for member in members:
                raw=member.orig_filename
                path=raw[len(prefix):].rstrip('/')
                if not path or member.is_dir():continue
                sub=PurePosixPath(path)
                if sub.is_absolute() or '..' in sub.parts or '.' in sub.parts:raise ValueError('Unsafe engine path')
                target=tmp.joinpath(*sub.parts);target.parent.mkdir(parents=True,exist_ok=True)
                with source.open(member) as inp,target.open('wb') as out:shutil.copyfileobj(inp,out,1024*1024)
            if not (tmp/'api_v2.py').is_file():raise ValueError('Downloaded engine lacks api_v2.py')
            (tmp/'.avt_engine_source.json').write_text(json.dumps({'commit':commit,'source':'https://github.com/RVC-Boss/GPT-SoVITS','source_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},indent=2)+'\n',encoding='utf-8')
            tmp.rename(destination)

def fetch(destination:Path,commit:str)->None:
    url=f'https://github.com/RVC-Boss/GPT-SoVITS/archive/{commit}.zip'
    with tempfile.TemporaryDirectory(prefix='avt_fetch_') as td:
        path=Path(td)/'source.zip';size=0
        with urlopen(Request(url,headers={'User-Agent':'AnimeVoiceTutor-Installer/0.13'}),timeout=90) as response,path.open('wb') as out:
            while chunk:=response.read(1024*1024):
                size+=len(chunk)
                if size>MAX_DOWNLOAD:raise ValueError('Engine source ZIP download too large')
                out.write(chunk)
        extract_pinned(path,destination,commit)
    print('PINNED_ENGINE_SOURCE_INSTALLED:',destination)

def main():
    p=argparse.ArgumentParser();p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--commit',required=True)
    args=p.parse_args();fetch(args.destination,args.commit)
if __name__=='__main__':main()
