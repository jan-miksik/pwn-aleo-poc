#!/usr/bin/env python3
"""Hands-on check of the two PoC flows against the LIVE public testnet.

Reads nothing from artifacts/ or .testnet/: every transaction and mapping value is
fetched from the explorer API right now, so what it prints is what anyone can see.
Only the two public addresses (testnet/*.public.json) are used, to prove they are
absent from the lending transactions.

    python3 scripts/verify_flow.py
"""
import json, re, sys, urllib.request
from pathlib import Path

API = 'https://api.explorer.provable.com/v1/testnet'
EXPLORER = 'https://testnet.explorer.provable.com/transaction/'
ROOT = Path(__file__).resolve().parents[1]
ADDRESS = re.compile(r'aleo1[a-z0-9]{58}')
STATUS = {'1u8': 'active', '2u8': 'repaid', '3u8': 'defaulted'}

HAPPY = [  # (who, what we expect to see, tx id)
    ('lender',   'open_commitment: lender escrows 400,000 credits under commitment 1field',
     'at1kjszxytexcksnff27xpaxz9udpnalkqy8txn6agwq9vskpg4lqxqallq5c'),
    ('borrower', 'accept: borrower locks 300,000 collateral, draws 200,000 -> loan 11field, owes 220,000',
     'at1aupepr5au4h6dkgmwhkwlrdcpd4dzyu2zks7jx90yddekg04avgqgyl8ds'),
    ('lender',   'claim_default TOO EARLY on loan 11field: rejected by the chain, collateral stays locked '
                 '(this run paid a public fee -> SEC-02 leak, fixed in the client since)',
     'at18p959h0up8nddnq3eakew9acfqsqvxfxehsg3ef26ymmu0vpjsgs3ez34j'),
    ('borrower', 'repay: borrower pays 220,000, gets 300,000 collateral back',
     'at1d37ge98wq96crex800n06janp3e3c4azpx462qyzzd2zz04ejs9qlacc64'),
    ('lender',   'withdraw_repayment: lender takes the 220,000 out of escrow',
     'at1h7fdl2rjhuvwfdwvj09scrkaff53j0mm7m2x46ytux0gdxjgzu8qlzsss6'),
    ('lender',   'cancel_commitment: lender takes the unused 200,000 back',
     'at18xxsy240hw8e8046kjuhr96mtu0rgwdymwyrc0xh7y3cwxgg6srqx7kya3'),
]
DEFAULT = [
    ('lender',   'open_commitment: lender escrows 300,000 credits under commitment 2field',
     'at1l5fe5hrnjypzswnucuj726e4qxd7pm6tzec8gmd6x8lc9d5j2v8sxsw833'),
    ('borrower', 'accept: borrower locks 450,000 collateral, draws 300,000 -> loan 12field (20 blocks)',
     'at1lwtesxgngk2wqkk3j6k4pwjszfhmpj0gf7w3t2pu3ecnj8z87yyq82fudd'),
    ('lender',   'claim_default after maturity: lender pulls the 450,000 collateral',
     'at14qfk6m64a7q70c4ev043esx6gud7705f79erks06hqg37gcd0srqkqyn7e'),
]


def get(path):
    req = urllib.request.Request(f'{API}/{path}', headers={'User-Agent': 'pwn-poc-verify/1'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def show_tx(actor, story, tx_id, people):
    tx = get(f'transaction/{tx_id}')
    confirmed = get(f'transaction/confirmed/{tx_id}')
    status = confirmed.get('status', '?')
    execution = tx.get('execution') or confirmed.get('rejected', {}).get('execution') or {'transitions': []}
    print(f'\n  [{actor}] {story}')
    print(f'      tx {EXPLORER}{tx_id}')
    print(f'      status={status}  fee={tx["fee"]["transition"]["function"]}')
    for tr in execution['transitions']:
        shown = []
        for v in tr['inputs'] + tr['outputs']:
            if v['type'] != 'public':
                continue
            if v['value'].startswith('{'):   # Terms / Loan struct: name the amount fields
                shown += [f'{k}={int(n):,}' for k, n in re.findall(r'(\w+_amount|min_draw|max_draw):\s*(\d+)u', v['value'])]
            elif re.fullmatch(r'\d+u(64|128)', v['value']):
                shown.append(f'{int(v["value"].rstrip("u12468")):,}')
        print(f'      {tr["program"]}::{tr["function"]}   public: {", ".join(shown) or "-"}')
    found = set(ADDRESS.findall(json.dumps(tx)) + ADDRESS.findall(json.dumps(confirmed)))
    leaks = [name for name, addr in people.items() if addr in found]
    other = len(found - set(people.values()))
    verdict = f'LEAK: {", ".join(leaks)} address is public' if leaks else 'OK: neither lender nor borrower address anywhere'
    print(f'      addresses in tx: {other} program/escrow address(es), {verdict}')
    return not leaks


def show_state(commitment, loan):
    st = get(f'program/pwn_loan_demo.aleo/mapping/loans/{loan}')
    status = re.search(r'status:\s*(\d+u8)', st).group(1)
    maturity = re.search(r'maturity:\s*(\d+)u32', st).group(1)
    print(f'\n  on-chain now: loan {loan} status={STATUS[status]}  maturity block {int(maturity):,}')
    print(f'                commitment {commitment}: available_credit='
          f'{get(f"program/pwn_elastic_proposal_demo.aleo/mapping/available_credit/{commitment}")}, '
          f'closed={get(f"program/pwn_elastic_proposal_demo.aleo/mapping/closed/{commitment}")}, '
          f'unwithdrawn repayments={get(f"program/pwn_elastic_proposal_demo.aleo/mapping/repayments/{commitment}")}')
    print(f'                (mapping holds only a hash + maturity + status: no amounts, no addresses)')


def main():
    people = {k: json.loads((ROOT / f'testnet/{f}.public.json').read_text())['address']
              for k, f in (('lender', 'account'), ('borrower', 'borrower'))}
    print(f'lender   {people["lender"]}\nborrower {people["borrower"]}')
    print(f'height   {get("block/height/latest"):,}')
    ok = True
    print('\n=== HAPPY PATH (commitment 1field, loan 11field) ===')
    for step in HAPPY:
        ok &= show_tx(*step, people)
    show_state('1field', '11field')
    print('\n=== DEFAULT PATH (commitment 2field, loan 12field) ===')
    for step in DEFAULT:
        ok &= show_tx(*step, people)
    show_state('2field', '12field')
    print('\nRESULT:', 'all lending transactions hide both participants' if ok
          else 'at least one lending transaction exposes a participant (expected: the early claim_default, SEC-02)')


if __name__ == '__main__':
    sys.exit(main())
