"""Read public Aleo mainnet bytecode and mappings; never submit transactions."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parent
API = 'https://api.explorer.provable.com/v1/mainnet'
PROGRAMS = '''credits.aleo puzzle_arcade_coin_v002.aleo token_registry.aleo
puzzle_arcade_ticket_v002.aleo pondo_protocol.aleo shield_swap.aleo
shield_swap_router.aleo usdcx_stablecoin.aleo usad_stablecoin.aleo
arc20_sol.aleo arc20_wbtc.aleo usdcx_bridge.aleo usdcx_bridge_v2.aleo
usad_bridge.aleo usdcx_multisig_core.aleo usad_multisig_core.aleo
arc20_multisig_core.aleo usdcx_freezelist.aleo usad_freezelist.aleo'''.split()

def fetch(program):
    url = f'{API}/program/{program}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'pwn-grant-research'})
        with urllib.request.urlopen(req, timeout=30) as response:
            code = json.load(response)
        if not isinstance(code, str) or 'program ' not in code:
            raise ValueError(str(code)[:100])
        (ROOT / program).write_text(code)
        constructor = code.split('constructor:', 1)[1].strip() if 'constructor:' in code else None
        return dict(program=program, url=url, sha256=hashlib.sha256(code.encode()).hexdigest(),
                    constructor=constructor, imports=[x for x in code.splitlines() if x.startswith('import ')],
                    burns=[x for x in code.splitlines() if x.startswith('function ') and 'burn' in x])
    except Exception as exc:
        return dict(program=program, url=url, error=str(exc))

if __name__ == '__main__':
    ROOT.mkdir(parents=True, exist_ok=True)
    if (ROOT / 'ranking.json').exists():
        ranking = json.loads((ROOT / 'ranking.json').read_text())['rankings']
        for rows in ranking.values():
            PROGRAMS.extend(row['program_id'] for row in rows[:20])
        PROGRAMS.extend(['shield_swap_multisig_core.aleo', 'shield_swap_arc20_wrapped_usdcx.aleo', 'shield_swap_arc20_credits.aleo'])
        PROGRAMS = list(dict.fromkeys(PROGRAMS))
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(fetch, PROGRAMS))
    (ROOT / 'program-evidence.json').write_text(json.dumps(dict(checked_date='2026-10-07', network='mainnet', programs=results), indent=2))
    for row in results:
        print(row['program'], row.get('error') or ('constructor ' + str(row['constructor'])[:400]), 'burns', row.get('burns', []))
