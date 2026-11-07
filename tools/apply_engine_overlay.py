"""Apply a reviewed, declarative engine compatibility overlay ZIP.

Never executes arbitrary scripts from ZIP. Each replacement requires a matching
original file SHA-256 and replacement SHA-256. Original bytes are backed up.
For security, use patches from a source you trust; patched Python executes later.
"""
from __future__ import annotations
import argparse,hashlib,json,re,shutil,stat,tempfile,zipfile
from pathlib import Path,PurePosixPath

ALLOWED = ('GPT_SoVITS/','api_v2.py')
MAX_BYTES=50*1024**2

def digest(b:bytes)->str:return hashlib.sha256(b).hexdigest()

def apply(archive:Path,engine:Path,*,dry_run:bool=False)->list[str]:
    archive=archive.resolve();engine=engine.resolve()
    if not (engine/'api_v2.py').is_file():raise ValueError('Engine api_v2.py missing')
    with zipfile.ZipFile(archive) as z:
        members=z.infolist();names=set()
        for m in members:
            raw=m.orig_filename
            if raw!=m.filename or not raw or '\\' in raw or raw.startswith('/') or ':' in raw or '\x00' in raw or ((m.external_attr>>16)&0o170000)==stat.S_IFLNK:
                raise ValueError('Unsafe overlay archive name')
            if any(p in ('','.','..') for p in raw.rstrip('/').split('/')):raise ValueError('Unsafe overlay archive path')
            if raw in names:raise ValueError('Duplicate overlay archive entry')
            names.add(raw)
        if 'engine_overlay.json' not in names:raise ValueError('Missing engine_overlay.json')
        config=json.loads(z.read('engine_overlay.json'))
        if config.get('schema_version')!=1 or config.get('type')!='avt-engine-overlay':raise ValueError('Wrong overlay format')
        specs=config.get('files')
        if not isinstance(specs,list) or not specs or len(specs)>30:raise ValueError('Empty or oversized overlay')
        staged=[];total=0;seen=set()
        for item in specs:
            rel=item.get('path')
            if not isinstance(rel,str) or rel in seen or '\\' in rel or rel.startswith('/') or ':' in rel:raise ValueError('Invalid overlay destination')
            seen.add(rel)
            parts=PurePosixPath(rel).parts
            if '..' in parts or '.' in parts or not (rel.startswith('GPT_SoVITS/') or rel=='api_v2.py') or not rel.endswith(('.py','.yaml','.yml','.json','.dict','.txt','.md5')):
                raise ValueError('Disallowed engine file')
            before=item.get('before_sha256');after=item.get('after_sha256')
            if not all(isinstance(x,str) and re.fullmatch('[0-9a-fA-F]{64}',x) for x in (before,after)):
                raise ValueError('File SHA-256 missing')
            asset='payload/'+rel
            if asset not in names:raise ValueError('Missing overlay payload file')
            target=engine.joinpath(*parts)
            if not target.is_file() or target.is_symlink() or not target.resolve().is_relative_to(engine):raise ValueError('Target missing or outside engine')
            original=target.read_bytes();replacement=z.read(asset)
            total+=len(replacement)
            if total>MAX_BYTES:raise ValueError('Overlay exceeds maximum size')
            if digest(original)!=before.lower() or digest(replacement)!=after.lower():raise ValueError('Engine overlay hash mismatch: '+rel)
            staged.append((target,rel,original,replacement))
        if dry_run:return [x[1] for x in staged]
        backup_root=engine.parent/(engine.name+'_avt_overlay_backup')
        backup_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=backup_root,prefix='overlay_') as td:
            backup=Path(td)
            for target,rel,original,_ in staged:
                p=backup/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(original)
            # Backups persisted BEFORE any destination writes.
            kept=backup_root/('backup_'+__import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
            backup.rename(kept)
            changed=[]
            try:
                for target,rel,_,replacement in staged:
                    tmp=target.with_name(target.name+'.avt_new')
                    tmp.write_bytes(replacement)
                    tmp.replace(target);changed.append((target,rel))
            except Exception:
                for target,rel in reversed(changed):target.write_bytes((kept/rel).read_bytes())
                raise
        return [x[1] for x in staged]

def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--engine',type=Path,required=True);p.add_argument('--dry-run',action='store_true')
    o=p.parse_args();paths=apply(o.archive,o.engine,dry_run=o.dry_run)
    print('ENGINE_OVERLAY_PREVIEW:' if o.dry_run else 'ENGINE_OVERLAY_APPLIED:',len(paths))
    for path in paths:print('FILE:',path)
if __name__=='__main__':main()
