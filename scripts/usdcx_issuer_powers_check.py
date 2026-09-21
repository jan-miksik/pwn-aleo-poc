#!/usr/bin/env python3
"""Read-only check of USDCx issuer powers on Aleo mainnet (SEC-01 evidence).

Reads only public program bytecode and public mapping values; never signs or
submits anything.  Fails loudly if the reviewed facts no longer hold, so it can
be re-run before any change to the collateral policy.
"""
import json
import sys
import urllib.request

API = 'https://api.explorer.provable.com/v1/mainnet'
PROGRAM = 'usdcx_stablecoin.aleo'

# Role bits as used by usdcx_stablecoin.aleo finalize blocks.
MINTER, BURNER, PAUSER, ADMIN = 1, 2, 4, 8

# All holders of address_to_role as of 2026-09-16 (aleoscan key count: 4).
# Traced from initialize (block 14,277,972) and the admin's update_role calls
# (blocks 14,277,976 / 14,277,979 / 19,336,870).
EXPECTED_ROLES = {
    'aleo13zt4uq0u09sffnf4ctgu47k5n30txjx2w9cwcqgneapjeqsywsqqu6hspt': (ADMIN, 'external account'),
    'aleo16s9af9darj0j5k7fpaxjq0u9fepd6sc4svrkr9vs4d3wlmp5lqyq4h3fpl': (PAUSER, 'external account'),
    'aleo1ezaara7fgypx7xfzrl4ruzqw9rg6t9juscpv83fw5hd27kezjqxscdzv7t': (MINTER | BURNER, 'usdcx_bridge.aleo'),
    'aleo16a4n2hcsekxra6k74tvle2c40f5ukfma06j5rltlagfnkr57g5yspj7jr0': (MINTER | BURNER, 'usdcx_bridge_v2.aleo'),
}

# The reviewed finalize block: burner role on the caller, no owner check.
BURN_PUBLIC_FINALIZE = """finalize burn_public:
    input r0 as address.public;
    input r1 as u128.public;
    input r2 as address.public;
    get address_to_role[r2] into r3;
    and r3 2u16 into r4;
    is.eq r4 2u16 into r5;
    assert.eq r5 true;
    get pause[true] into r6;
    assert.eq r6 false;
    get balances[r0] into r7;
    sub r7 r1 into r8;
    set r8 into balances[r0];"""


def get(path):
    req = urllib.request.Request(f'{API}/{path}', headers={'User-Agent': 'pwn-poc-review'})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def main():
    failures = []
    program = get(f'program/{PROGRAM}')
    if BURN_PUBLIC_FINALIZE not in program:
        failures.append('burn_public finalize differs from the reviewed bytecode')
    for bridge in ('usdcx_bridge.aleo', 'usdcx_bridge_v2.aleo'):
        code = get(f'program/{bridge}')
        if f'call {PROGRAM}/burn_public self.caller r0' not in code:
            failures.append(f'{bridge} burn_public no longer restricted to self.caller')
    for address, (role, who) in EXPECTED_ROLES.items():
        value = get(f'program/{PROGRAM}/mapping/address_to_role/{address}')
        actual = int(str(value).strip('"').rstrip('u16')) if value else 0
        print(f'{address}  role={actual:<2} expected={role:<2} {who}')
        if actual != role:
            failures.append(f'role of {who} changed: {actual} != {role}')
    paused = get(f'program/{PROGRAM}/mapping/pause/true')
    print(f'pause={paused}')
    if failures:
        print('\n'.join(f'FAIL: {f}' for f in failures))
        sys.exit(1)
    print('OK: only the two bridge programs hold BURNER; a single admin key can grant it.')


if __name__ == '__main__':
    main()
