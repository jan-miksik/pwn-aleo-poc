"""Fetch selected public governance keys; this does not enumerate all roles."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import re
import urllib.request

ROOT = Path(__file__).resolve().parent
API = 'https://api.explorer.provable.com/v1/mainnet'
queries = [('height', 'block/height/latest')]
queries.extend([
 ('pALEO metadata', 'program/token_registry.aleo/mapping/registered_tokens/1751493913335802797273486270793650302076377624243810059080883537084141842600field'),
 ('wrapped credits metadata', 'program/token_registry.aleo/mapping/registered_tokens/3443843282313283355522573239085696902919850365217539366784739393210722344986field'),
])
for program in ['usdcx_multisig_core.aleo', 'usad_multisig_core.aleo', 'arc20_multisig_core.aleo', 'shield_swap_multisig_core.aleo']:
    queries.append((program + ' settings', f'program/{program}/mapping/program_settings_map/true'))
for program in ['jusd_oracle_staging.aleo', 'jusd_oracle_production.aleo']:
    queries.append((program + ' upgrades_disabled', f'program/{program}/mapping/upgrades_disabled/true'))
addresses = ['aleo13zt4uq0u09sffnf4ctgu47k5n30txjx2w9cwcqgneapjeqsywsqqu6hspt',
'aleo16s9af9darj0j5k7fpaxjq0u9fepd6sc4svrkr9vs4d3wlmp5lqyq4h3fpl',
'aleo1ezaara7fgypx7xfzrl4ruzqw9rg6t9juscpv83fw5hd27kezjqxscdzv7t',
'aleo16a4n2hcsekxra6k74tvle2c40f5ukfma06j5rltlagfnkr57g5yspj7jr0']
for address in addresses:
    queries.append(('usdcx role ' + address, f'program/usdcx_stablecoin.aleo/mapping/address_to_role/{address}'))
for program in ['arc20_sol.aleo','arc20_wbtc.aleo','usad_stablecoin.aleo']:
    code = (ROOT / program).read_text()
    # Literal addresses provide candidate keys only, not a complete role census.
    candidates = set(re.findall(r'aleo1[a-z0-9]{58}', code))
    for address in candidates:
        queries.append((program + ' role ' + address, f'program/{program}/mapping/address_to_role/{address}'))

def fetch(item):
    label, path = item
    url = API + '/' + path
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'pwn-grant-research'})
        with urllib.request.urlopen(request, timeout=30) as response:
            value = json.load(response)
        return dict(label=label, url=url, value=value)
    except Exception as exc:
        return dict(label=label, url=url, error=str(exc))

if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows=list(pool.map(fetch, queries))
    (ROOT / 'state-evidence.json').write_text(json.dumps(dict(checked_date='2026-10-07', complete_role_enumeration=False, observations=rows), indent=2))
    for row in rows:
        if row.get('value') is not None or 'error' in row:
            print(row['label'], row.get('value', row.get('error')))
