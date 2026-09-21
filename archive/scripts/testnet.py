#!/usr/bin/env python3
"""Public Aleo testnet connection and isolated account setup. No transaction submission."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT/'testnet/config.json').read_text())
SECRET = ROOT/'.testnet/account.json'
PUBLIC = ROOT/'testnet/account.public.json'
EVIDENCE = ROOT/'artifacts/testnet'


def now(): return datetime.now(timezone.utc).isoformat()


def account():
    if not PUBLIC.exists():
        raise SystemExit('Run python3 scripts/testnet.py init first.')
    return json.loads(PUBLIC.read_text())


def init():
    if SECRET.exists():
        # Retain the existing key. Only read/export the public address.
        data = json.loads(SECRET.read_text())
        pub = {k: data[k] for k in ('network','address','created_at')}
    else:
        SECRET.parent.mkdir(mode=0o700, exist_ok=True)
        os.chmod(SECRET.parent, 0o700)
        result = subprocess.run([str(ROOT/'scripts/leo'), 'account', 'new',
            '--network','testnet','--endpoint',CONFIG['endpoint']], cwd=ROOT,
            text=True, capture_output=True)
        if result.returncode:
            raise SystemExit('Leo account creation failed; output suppressed to avoid logging key material.')
        private = re.search(r'APrivateKey\w+', result.stdout)
        address = re.search(r'aleo1[a-z0-9]+', result.stdout)
        if not private or not address:
            raise SystemExit('Unexpected Leo account output; output not logged.')
        data = {'network':'testnet','address':address.group(),
            'private_key':private.group(),'created_at':now()}
        fd = os.open(SECRET, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with os.fdopen(fd,'w') as f: json.dump(data,f,indent=2);f.write('\n')
        pub = {k:data[k] for k in ('network','address','created_at')}
    if pub['network'] != 'testnet': raise SystemExit('Refusing a non-testnet account.')
    PUBLIC.write_text(json.dumps(pub,indent=2)+'\n')
    print(json.dumps(pub,indent=2))


def get(path):
    url = CONFIG['endpoint'].rstrip('/')+'/testnet/'+path
    request = urllib.request.Request(url, headers={'User-Agent':'pwn-aleo-feasibility-poc','Accept':'application/json'})
    with urllib.request.urlopen(request,timeout=30) as r:
        return json.load(r)


def status():
    if CONFIG['network'] != 'testnet': raise SystemExit('This profile supports testnet only.')
    public = account();address = public['address']
    queries = {
        'latest_height':'block/height/latest',
        'latest_block':'block/latest',
        'credits_public_balance':f'program/credits.aleo/mapping/account/{address}',
        'usdcx_public_balance':f"program/{CONFIG['usdcx_program']}/mapping/balances/{address}",
        'usdcx_paused':f"program/{CONFIG['usdcx_program']}/mapping/pause/true",
        'freeze_root':f"program/{CONFIG['freezelist_program']}/mapping/freeze_list_root/1u8",
    }
    values={};errors={}
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending={name:pool.submit(get,path) for name,path in queries.items()}
        for name,future in pending.items():
            try: values[name]=future.result()
            except Exception as e: errors[name]=str(e)
    block=values.pop('latest_block',{})
    metadata=block.get('header',{}).get('metadata',{})
    report={'checked_at':now(),'network':'testnet','endpoint':CONFIG['endpoint'],
        'address':address,'consensus_version':'not exposed by this API endpoint','block_hash':block.get('block_hash'),
        'block_timestamp':metadata.get('timestamp'),
        **values,'private_balances':'not scanned','errors':errors}
    report['connected']=isinstance(values.get('latest_height'),int) and bool(report['block_hash'])
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    (EVIDENCE/'connection.json').write_text(json.dumps(report,indent=2)+'\n')
    if block: (EVIDENCE/'latest-block.json').write_text(json.dumps(block,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['connected'] or errors: raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['init','status','address'])
    command=parser.parse_args().command
    if command=='init':init()
    elif command=='status':status()
    else:print(account()['address'])
