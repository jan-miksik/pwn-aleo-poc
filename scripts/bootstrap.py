#!/usr/bin/env python3
"""Install official pinned Leo compiler locally; no global PATH changes."""
import hashlib,json,platform,stat,urllib.request,zipfile,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='leo-lang-v4.4.2'
arch={'arm64':'aarch64','aarch64':'aarch64','x86_64':'x86_64','AMD64':'x86_64'}[platform.machine()]
os_name={'Darwin':'apple-darwin','Linux':'unknown-linux-gnu','Windows':'pc-windows-msvc'}[platform.system()]
asset=f'{VERSION}-{arch}-{os_name}.zip'
api=f'https://api.github.com/repos/ProvableHQ/leo/releases/tags/{VERSION}'
req=urllib.request.Request(api,headers={'User-Agent':'pwn-aleo-poc'})
with urllib.request.urlopen(req) as r: metadata=json.load(r)
release=next(x for x in metadata['assets'] if x['name']==asset)
with urllib.request.urlopen(release['browser_download_url']) as r: payload=r.read()
digest=release.get('digest')
if not digest or not digest.startswith('sha256:'): raise RuntimeError('Official release has no SHA-256 digest; verify manually')
assert hashlib.sha256(payload).hexdigest()==digest.split(':',1)[1], 'Release checksum mismatch'
target=ROOT/'.tools';target.mkdir(exist_ok=True)
with zipfile.ZipFile(io.BytesIO(payload)) as archive:
 member='leo.exe' if platform.system()=='Windows' else 'leo'
 (target/member).write_bytes(archive.read(member))
 (target/member).chmod((target/member).stat().st_mode|stat.S_IXUSR)
print('Installed',VERSION,'to',target)
