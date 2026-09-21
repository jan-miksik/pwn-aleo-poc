#!/usr/bin/env python3
"""Resumable end-to-end PWN lending lifecycle on the public Aleo testnet.

Deployed `_demo` programs, real proofs, real network finalization. Every step is
prepared locally, broadcast, and confirmed separately; a confirmed step is never
re-executed. Every lending flow pays a private fee, including flows expected to be
rejected. Secrets, salts and plaintext records stay in .testnet/lifecycle*;
artifacts/testnet/lifecycle* holds only chain-visible data and summaries.

Runs:
  python3 scripts/testnet_lifecycle.py          # run 1 (2026-09-16): setup + full lifecycle, done
  python3 scripts/testnet_lifecycle.py run2     # run 2: lifecycle only, after SECURITY-REVIEW.md
                                                #   SEC-02 (private fee on the rejected claim),
                                                #   SEC-03 (one salt per position) and SEC-04
                                                #   (random IDs); funded from run-1 leftover records
  python3 scripts/testnet_lifecycle.py summary [run2]
"""
import json, os, re, secrets, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path
from testnet import ROOT, CONFIG, SECRET, now

RUN = 'run2' if 'run2' in sys.argv[1:] else 'run1'
LOCAL = ROOT / ('.testnet/lifecycle' if RUN == 'run1' else '.testnet/lifecycle-' + RUN)
PUBLIC = ROOT / ('artifacts/testnet/lifecycle' if RUN == 'run1' else 'artifacts/testnet/lifecycle-' + RUN)
RUN1_LOCAL = ROOT / '.testnet/lifecycle'
BORROWER_SECRET = ROOT / '.testnet/borrower.json'
ENTRY = ROOT / 'testnet/programs/pwn_loan_demo'
STATE = LOCAL / 'state.json'
PRIVATE_FEE_FLOWS = {'open_commitment', 'accept', 'repay', 'claim_default', 'cancel_commitment', 'withdraw_repayment'}
LEO = str(ROOT / 'scripts/leo')


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def rpc(path, body=None):
    req = urllib.request.Request(CONFIG['endpoint'] + '/testnet/' + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={'Content-Type': 'application/json', 'User-Agent': 'pwn-aleo-poc'})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def mapping(program, name, key):
    try:
        return rpc(f'program/{program}/mapping/{name}/{key}')
    except urllib.error.HTTPError as error:
        if error.code == 404 or error.code == 500:
            return None
        raise


def height():
    return int(rpc('block/height/latest'))


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {'steps': {}, 'checks': []}


def save_state(state):
    write(STATE, state)


def borrower():
    if not BORROWER_SECRET.exists():
        result = subprocess.run([LEO, 'account', 'new', '--network', 'testnet'], cwd=ROOT, text=True, capture_output=True)
        assert result.returncode == 0, 'borrower account creation failed (output withheld)'
        data = {'network': 'testnet', 'address': re.search(r'aleo1[a-z0-9]+', result.stdout).group(),
                'private_key': re.search(r'APrivateKey\w+', result.stdout).group(), 'created_at': now(), 'role': 'borrower'}
        fd = os.open(BORROWER_SECRET, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, indent=2)
        write(ROOT / 'testnet/borrower.public.json', {k: data[k] for k in ('network', 'address', 'created_at', 'role')})
    return json.loads(BORROWER_SECRET.read_text())


ACTORS = {'lender': json.loads(SECRET.read_text()), 'borrower': borrower()}
ADDR = {k: v['address'] for k, v in ACTORS.items()}


def leo(args, actor, log_path, cwd=ROOT):
    env = dict(os.environ, PRIVATE_KEY=ACTORS[actor]['private_key'], NETWORK='testnet', ENDPOINT=CONFIG['endpoint'])
    for name in ('DEVNET', 'CONSENSUS_VERSION', 'CONSENSUS_HEIGHTS'):
        env.pop(name, None)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    clock = time.perf_counter()
    with log_path.open('w') as log:
        proc = subprocess.run([LEO, *map(str, args)], env=env, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
    return proc.returncode, round(time.perf_counter() - clock, 3), re.sub(r'\x1b\[[0-9;]*m', '', log_path.read_text())


def record_out(label, index):
    """Plaintext of the index-th top-level output of a confirmed step (Leo decrypts owned records locally).

    Cross-program records appear on chain only as an `external_record` reference in the caller
    transition, so the ciphertext cannot be matched reliably; the local plaintext is used instead.
    """
    value = json.loads((LOCAL / label / 'result.json').read_text())['outputs'][index]
    assert value.startswith('{') and 'owner:' in value, f'{label}[{index}] is not a record'
    return value


def fee_change(label):
    tx = json.loads((LOCAL / label / 'transaction.execution.json').read_text())
    fee = tx['fee']['transition']
    assert fee['function'] == 'fee_private'
    return fee['outputs'][0]['value']


def plain_out(label, index):
    return json.loads((LOCAL / label / 'result.json').read_text())['outputs'][index]


def step(label, actor, function, inputs, fee_record=None, expect='accepted'):
    """expect: accepted | rejected (network finalize failure) | local_fail (proof-time assert)."""
    state = load_state()
    entry = state['steps'].get(label, {})
    if entry.get('phase') == 'done':
        print(f'skip {label}: {entry["status"]}')
        return entry
    local, public = LOCAL / label, PUBLIC / label
    local.mkdir(parents=True, exist_ok=True)
    name = function.split('::')[-1]
    # SEC-02: a rejected execution is published next to its fee, so an expected rejection
    # with a public fee links the payer to the full public Loan witness. No fallback.
    if fee_record is None and name in PRIVATE_FEE_FLOWS:
        raise SystemExit(f'{label}: lending flows must pay private fees, also when expect={expect}')
    if entry.get('phase') not in ('prepared', 'submitted'):
        args = ['execute', function, *inputs, '--path', ENTRY, '--network', 'testnet', '--endpoint', CONFIG['endpoint'],
                '--save', local, '--yes', '--json-output=' + str(local / 'result.json')]
        if fee_record:
            args += ['--fee-records', fee_record]
        print(f'prepare {label} ({actor}, {function})', flush=True)
        code, seconds, log = leo(args, actor, local / 'leo.log')
        entry = {'actor': actor, 'function': function, 'fee_mode': 'private' if fee_record else 'public',
                 'expect': expect, 'prepare_wall_seconds': seconds, 'prepare_exit_code': code, 'started_at': now()}
        if expect == 'local_fail':
            assert code != 0 and not (local / 'transaction.execution.json').exists(), f'{label}: expected local failure'
            entry.update(phase='done', status='local_fail', transaction_id=None,
                         reason=(re.search(r'(assert|halted|failed)[^\n]*', log, re.I) or [''])[0][:200])
            state['steps'][label] = entry; save_state(state)
            write(public / 'audit.json', {k: v for k, v in entry.items()} | {'label': label, 'note': 'No transaction created; execution aborted at proof time. No fee paid.'})
            print(f'  local failure as expected'); return entry
        assert code == 0 and (local / 'transaction.execution.json').exists(), f'{label}: preparation failed, see {local}/leo.log'
        tx = json.loads((local / 'transaction.execution.json').read_text())
        result = json.loads((local / 'result.json').read_text())
        entry.update(phase='prepared', transaction_id=tx['id'], fee_microcredits=result['stats']['total_cost'],
                     fee_function=tx['fee']['transition']['function'])
        state['steps'][label] = entry; save_state(state)
    tx = json.loads((local / 'transaction.execution.json').read_text())
    if entry.get('phase') == 'prepared':
        entry['submitted_at'] = now(); entry['phase'] = 'submitted'
        state['steps'][label] = entry; save_state(state)  # persisted before I/O: never double-broadcast
        response = rpc('transaction/broadcast', tx)
        entry['broadcast_response'] = response
        state['steps'][label] = entry; save_state(state)
        print(f'  broadcast {tx["id"]}', flush=True)
    for _ in range(40):
        try:
            receipt = rpc('transaction/confirmed/' + tx['id']); break
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            time.sleep(5)
    else:
        raise SystemExit(f'{label}: not confirmed after 200 s; rerun to continue polling')
    # A rejected execution is recorded as a fee-only transaction under a new id.
    block_hash = rpc('find/blockHash/' + receipt['transaction']['id'])
    meta = rpc('block/' + block_hash)['header']['metadata']
    entry.update(phase='done', status=receipt['status'], block_height=meta['height'], block_timestamp=meta['timestamp'],
                 confirmed_at=now(), on_chain_transaction_id=receipt['transaction']['id'])
    assert receipt['status'] == expect, f'{label}: expected {expect}, got {receipt["status"]}'
    state['steps'][label] = entry; save_state(state)
    chain = receipt['transaction']
    serialized = json.dumps(receipt)
    # A rejected transaction keeps only its fee on chain; the rejected execution sits beside it.
    execution = chain.get('execution') or receipt.get('rejected', {}).get('execution') or {'transitions': []}
    transitions = execution.get('transitions', [])
    audit = {'label': label, **{k: v for k, v in entry.items() if k != 'broadcast_response'},
             'execution_transitions': [(t['program'], t['function']) for t in transitions],
             'top_level_input_types': [i['type'] for i in transitions[-1]['inputs']] if transitions else None,
             'top_level_output_types': [o['type'] for o in transitions[-1]['outputs']] if transitions else None,
             'fee_input_types': [i['type'] for i in chain['fee']['transition']['inputs']],
             'lender_address_on_chain': ADDR['lender'] in serialized,
             'borrower_address_on_chain': ADDR['borrower'] in serialized,
             'addresses_on_chain': sorted(set(re.findall(r'aleo1[a-z0-9]{58}', serialized)))}
    write(public / 'transaction.json', receipt)
    write(public / 'audit.json', audit)
    print(f'  {receipt["status"]} in block {meta["height"]}; lender visible={audit["lender_address_on_chain"]} borrower visible={audit["borrower_address_on_chain"]}')
    return entry


def check(label, condition):
    state = load_state()
    if label in [c['check'] for c in state['checks']]:
        print('skip check (already passed):', label); return
    for _ in range(8):  # the public API can lag a few seconds behind the confirmed block
        if condition() if callable(condition) else condition:
            break
        time.sleep(5)
    else:
        raise AssertionError(label)
    if label not in [c['check'] for c in state['checks']]:
        state['checks'].append({'check': label, 'status': 'PASS', 'at': now()})
        save_state(state)
    print('PASS', label)


def state_value(name, make):
    """Persisted per run in .testnet: salts (secret), random IDs and the expiry (public once used)."""
    state = load_state()
    if name not in state:
        state[name] = make(); save_state(state)
    return state[name]


secret_value = state_value


def random_field():
    return str(secrets.randbelow(2**250))


def auth(domain, account, salt, tag=''):
    out = LOCAL / f'auth-{domain}{tag}.json'
    code, _, log = leo(['run', 'auth', f'{domain}u8', account, f'{salt}field', '--path', ROOT / 'testnet/programs/pwn_test_utils',
                        '--json-output=' + str(out)], 'lender', LOCAL / f'auth-{domain}{tag}.log')
    assert code == 0, log[-1000:]
    return json.loads(out.read_text())['outputs'][0]


def run1_record(label, index):
    """Plaintext of a run-1 output record left over after the first lifecycle (lender/borrower change, refunds)."""
    value = json.loads((RUN1_LOCAL / label / 'result.json').read_text())['outputs'][index]
    assert value.startswith('{') and 'owner:' in value, f'run1 {label}[{index}] is not a record'
    return value


def run1_fee_change(label):
    tx = json.loads((RUN1_LOCAL / label / 'transaction.execution.json').read_text())
    fee = tx['fee']['transition']
    assert fee['function'] == 'fee_private'
    return fee['outputs'][0]['value']


def terms(token, duration, expiry, lender_auth, min_draw=100000, max_draw=300000):
    return ('{ credit_asset: credits.aleo, collateral_asset: ' + token + f', min_draw: {min_draw}u64, max_draw: {max_draw}u64, '
            'collateral_ratio: 15000u64, repayment_ratio: 11000u64, duration: ' + str(duration) + 'u32, expiry: '
            + str(expiry) + 'u32, lender_auth: ' + lender_auth + ' }')


def main():
    os.umask(0o077)
    LOCAL.mkdir(parents=True, exist_ok=True)
    L, B = ADDR['lender'], ADDR['borrower']
    print('run', RUN); print('lender', L); print('borrower', B)
    (run1 if RUN == 'run1' else run2)(L, B)
    summary()


def run1(L, B):
    """First lifecycle (2026-09-16). Kept verbatim as the record of what ran; every step is confirmed and skipped.

    Known privacy defects of this run, kept as evidence (SECURITY-REVIEW.md): one lender and one borrower
    salt for all positions (SEC-03), predictable IDs 1/2/11/12 (SEC-04), and step 14 with a public fee (SEC-02;
    since fixed in step(), so this run would now stop at 14 if it were not already confirmed).
    """
    token = secret_value('token_id', lambda: str(secrets.randbelow(2**250)) + 'field')
    lender_salt = secret_value('lender_salt', lambda: str(secrets.randbelow(2**250)))
    borrower_salt = secret_value('borrower_salt', lambda: str(secrets.randbelow(2**250)))
    expiry = secret_value('expiry', lambda: height() + 20000)
    lender_auth = auth(1, L, lender_salt)

    # --- setup: public fees, deployer/admin
    step('01-initialize', 'lender', 'pwn_config_demo.aleo::initialize', [])
    check('config initialized with deployer admin', lambda: L in (mapping('pwn_config_demo.aleo', 'settings', 'true') or ''))
    step('02-hub-approve-proposal', 'lender', 'pwn_hub_demo.aleo::set_tag', ['pwn_elastic_proposal_demo.aleo', '2u8', 'true'])
    step('03-hub-approve-loan', 'lender', 'pwn_hub_demo.aleo::set_tag', ['pwn_loan_demo.aleo', '1u8', 'true'])
    assert mapping('token_registry.aleo', 'registered_tokens', token) is None or load_state()['steps'].get('04-register-token'), 'token id collision'
    step('04-register-token', 'lender', 'token_registry.aleo::register_token',
         [token, '1347374349u128', '1347374349u128', '6u8', '1000000000000u128', 'false', L])
    check('test collateral token registered on live token_registry', lambda: mapping('token_registry.aleo', 'registered_tokens', token) is not None)
    step('05-fund-borrower', 'lender', 'credits.aleo::transfer_public', [B, '1500000u64'])
    step('06-mint-collateral', 'lender', 'token_registry.aleo::mint_private', [token, B, '1000000u128', 'false', '4294967295u32'])
    step('07-borrower-shield-repay-input', 'borrower', 'credits.aleo::transfer_public_to_private', [B, '500000u64'])
    step('08-borrower-shield-fee-record', 'borrower', 'credits.aleo::transfer_public_to_private', [B, '600000u64'])
    # lender private records from the fee experiment: 900,000 (transfer change) and 997,692 (fee change)
    previous = json.loads((ROOT / '.testnet/private-fee/private-transfer/transaction.execution.json').read_text())
    lender_credit = previous['execution']['transitions'][-1]['outputs'][1]['value']
    lender_fee = previous['fee']['transition']['outputs'][0]['value']

    # --- lending flows: private fees
    t1 = terms(token, 1500, expiry, lender_auth)   # ~75 min at 3 s/block: repaid loan
    t2 = terms(token, 20, expiry, lender_auth)     # ~1 min: defaulted loan
    step('09-open-commitment-1', 'lender', 'pwn_elastic_proposal_demo.aleo::open_commitment',
         ['1field', t1, lender_credit, '400000u64', lender_salt + 'field'], fee_record=lender_fee)
    check('commitment 1 funded with 400,000', lambda: mapping('pwn_elastic_proposal_demo.aleo', 'available_credit', '1field') == '400000u64')
    step('10-open-commitment-2', 'lender', 'pwn_elastic_proposal_demo.aleo::open_commitment',
         ['2field', t2, record_out('09-open-commitment-1', 0), '300000u64', lender_salt + 'field'], fee_record=fee_change('09-open-commitment-1'))
    check('commitment 2 funded with 300,000', lambda: mapping('pwn_elastic_proposal_demo.aleo', 'available_credit', '2field') == '300000u64')
    step('11-accept-overdraw-local', 'borrower', 'pwn_loan_demo.aleo::accept',
         ['11field', '1field', t1, '350000u64', record_out('06-mint-collateral', 0), borrower_salt + 'field'],
         fee_record=record_out('08-borrower-shield-fee-record', 0), expect='local_fail')
    step('12-accept-loan-1', 'borrower', 'pwn_loan_demo.aleo::accept',
         ['11field', '1field', t1, '200000u64', record_out('06-mint-collateral', 0), borrower_salt + 'field'],
         fee_record=record_out('08-borrower-shield-fee-record', 0))
    check('loan 1 active; commitment 1 reduced to 200,000 without lender signing',
          lambda: 'status: 1u8' in (mapping('pwn_loan_demo.aleo', 'loans', '11field') or '') and mapping('pwn_elastic_proposal_demo.aleo', 'available_credit', '1field') == '200000u64')
    witness1 = plain_out('12-accept-loan-1', 2)
    step('13-accept-loan-2', 'borrower', 'pwn_loan_demo.aleo::accept',
         ['12field', '2field', t2, '300000u64', record_out('12-accept-loan-1', 1), borrower_salt + 'field'],
         fee_record=fee_change('12-accept-loan-1'))
    check('loan 2 exhausts commitment 2', lambda: mapping('pwn_elastic_proposal_demo.aleo', 'available_credit', '2field') == '0u64')
    witness2 = plain_out('13-accept-loan-2', 2)
    # Loan 1 matures ~1500 blocks later: the claim proves locally but network finalization rejects it.
    step('14-claim-default-early', 'lender', 'pwn_loan_demo.aleo::claim_default', [witness1, lender_salt + 'field'], expect='rejected')
    check('early default claim rejected by network finalization', lambda: 'status: 1u8' in mapping('pwn_loan_demo.aleo', 'loans', '11field'))
    step('15-repay-loan-1', 'borrower', 'pwn_loan_demo.aleo::repay',
         [witness1, record_out('07-borrower-shield-repay-input', 0), borrower_salt + 'field'], fee_record=fee_change('13-accept-loan-2'))
    check('loan 1 repaid; 220,000 allocated to commitment 1',
          lambda: 'status: 2u8' in mapping('pwn_loan_demo.aleo', 'loans', '11field') and mapping('pwn_elastic_proposal_demo.aleo', 'repayments', '1field') == '220000u64')
    maturity = int(re.search(r'maturity: (\d+)u32', mapping('pwn_loan_demo.aleo', 'loans', '12field')).group(1))
    while height() < maturity:
        print(f'  waiting for maturity {maturity}, height {height()}', flush=True); time.sleep(15)
    step('16-claim-default-loan-2', 'lender', 'pwn_loan_demo.aleo::claim_default', [witness2, lender_salt + 'field'],
         fee_record=fee_change('10-open-commitment-2'))
    check('lender claims collateral after maturity without borrower', lambda: 'status: 3u8' in mapping('pwn_loan_demo.aleo', 'loans', '12field'))
    step('17-withdraw-repayment', 'lender', 'pwn_elastic_proposal_demo.aleo::withdraw_repayment',
         ['1field', t1, lender_salt + 'field', '220000u64'], fee_record=fee_change('16-claim-default-loan-2'))
    check('lender privately withdrew repayment', lambda: mapping('pwn_elastic_proposal_demo.aleo', 'repayments', '1field') == '0u64')
    step('18-cancel-commitment-1', 'lender', 'pwn_elastic_proposal_demo.aleo::cancel_commitment',
         ['1field', t1, lender_salt + 'field', '200000u64'], fee_record=fee_change('17-withdraw-repayment'))
    check('unused 200,000 refunded privately and commitment closed',
          lambda: mapping('pwn_elastic_proposal_demo.aleo', 'closed', '1field') == 'true' and mapping('pwn_elastic_proposal_demo.aleo', 'available_credit', '1field') == '0u64')


def run2(L, B):
    """Second lifecycle after the security review. No setup steps: config, hub tags and the collateral token
    from run 1 are reused, and every input is a private record left over from run 1, so no new public
    shielding names either participant right before a lending call.

    Fixes exercised on chain: private fee on the expected-rejected early claim (SEC-02); a fresh salt per
    commitment and per loan, so lender/borrower hashes differ between positions (SEC-03); random IDs (SEC-04).
    Amounts are smaller than run 1 (100,000 draws) to fit the leftover records.
    """
    run1_state = json.loads((RUN1_LOCAL / 'state.json').read_text())
    assert run1_state['steps']['18-cancel-commitment-1'].get('phase') == 'done', 'run 1 must be complete'
    token = run1_state['token_id']
    cid = {i: state_value(f'commitment_id_{i}', lambda: random_field() + 'field') for i in (1, 2)}
    lid = {i: state_value(f'loan_id_{i}', lambda: random_field() + 'field') for i in (1, 2)}
    lender_salt = {i: state_value(f'lender_salt_{i}', random_field) for i in (1, 2)}
    borrower_salt = {i: state_value(f'borrower_salt_{i}', random_field) for i in (1, 2)}
    assert len({*lender_salt.values(), *borrower_salt.values(), run1_state['lender_salt'], run1_state['borrower_salt']}) == 6
    expiry = state_value('expiry', lambda: height() + 20000)
    lender_auth = {i: auth(1, L, lender_salt[i], tag=f'-c{i}') for i in (1, 2)}
    assert lender_auth[1] != lender_auth[2]
    write(PUBLIC / 'ids.json', {'commitment_ids': cid, 'loan_ids': lid, 'note': 'random per-run IDs (SEC-04); salts stay in .testnet'})

    # run-1 leftovers: lender 220,000 payout (17) + 200,000 refund (18) + fee change chain (18);
    # borrower 300,000 returned collateral (15), 250,000 collateral change (13), 280,000 repay change (15), fee change chain (15)
    t1 = terms(token, 400, expiry, lender_auth[1])   # ~20 min: repaid loan; early claim rejected first
    t2 = terms(token, 20, expiry, lender_auth[2])    # ~1 min: defaulted loan
    step('09-open-commitment-1', 'lender', 'pwn_elastic_proposal_demo.aleo::open_commitment',
         [cid[1], t1, run1_record('17-withdraw-repayment', 0), '200000u64', lender_salt[1] + 'field'], fee_record=run1_fee_change('18-cancel-commitment-1'))
    check('commitment 1 funded with 200,000', lambda: mapping('pwn_elastic_proposal_demo.aleo', 'available_credit', cid[1]) == '200000u64')
    step('10-open-commitment-2', 'lender', 'pwn_elastic_proposal_demo.aleo::open_commitment',
         [cid[2], t2, run1_record('18-cancel-commitment-1', 0), '100000u64', lender_salt[2] + 'field'], fee_record=fee_change('09-open-commitment-1'))
    check('commitment 2 funded with 100,000', lambda: mapping('pwn_elastic_proposal_demo.aleo', 'available_credit', cid[2]) == '100000u64')
    step('12-accept-loan-1', 'borrower', 'pwn_loan_demo.aleo::accept',
         [lid[1], cid[1], t1, '100000u64', run1_record('15-repay-loan-1', 1), borrower_salt[1] + 'field'],
         fee_record=run1_fee_change('15-repay-loan-1'))
    check('loan 1 active; commitment 1 reduced to 100,000',
          lambda: 'status: 1u8' in (mapping('pwn_loan_demo.aleo', 'loans', lid[1]) or '') and mapping('pwn_elastic_proposal_demo.aleo', 'available_credit', cid[1]) == '100000u64')
    witness1 = plain_out('12-accept-loan-1', 2)
    step('13-accept-loan-2', 'borrower', 'pwn_loan_demo.aleo::accept',
         [lid[2], cid[2], t2, '100000u64', run1_record('13-accept-loan-2', 1), borrower_salt[2] + 'field'],
         fee_record=fee_change('12-accept-loan-1'))
    check('loan 2 exhausts commitment 2', lambda: mapping('pwn_elastic_proposal_demo.aleo', 'available_credit', cid[2]) == '0u64')
    witness2 = plain_out('13-accept-loan-2', 2)
    assert re.search(r'borrower_auth: (\d+field)', witness1).group(1) != re.search(r'borrower_auth: (\d+field)', witness2).group(1)
    # SEC-02 regression: the expected network rejection now pays a private fee; the rejected execution
    # still publishes the Loan witness, but no fee payer address.
    step('14-claim-default-early', 'lender', 'pwn_loan_demo.aleo::claim_default', [witness1, lender_salt[1] + 'field'],
         fee_record=fee_change('10-open-commitment-2'), expect='rejected')
    check('early default claim rejected by network finalization', lambda: 'status: 1u8' in mapping('pwn_loan_demo.aleo', 'loans', lid[1]))
    check('rejected claim carries no participant address', lambda: not any(
        json.loads((PUBLIC / '14-claim-default-early/audit.json').read_text())[k] for k in ('lender_address_on_chain', 'borrower_address_on_chain')))
    step('15-repay-loan-1', 'borrower', 'pwn_loan_demo.aleo::repay',
         [witness1, run1_record('15-repay-loan-1', 0), borrower_salt[1] + 'field'], fee_record=fee_change('13-accept-loan-2'))
    check('loan 1 repaid; 110,000 allocated to commitment 1',
          lambda: 'status: 2u8' in mapping('pwn_loan_demo.aleo', 'loans', lid[1]) and mapping('pwn_elastic_proposal_demo.aleo', 'repayments', cid[1]) == '110000u64')
    maturity = int(re.search(r'maturity: (\d+)u32', mapping('pwn_loan_demo.aleo', 'loans', lid[2])).group(1))
    while height() < maturity:
        print(f'  waiting for maturity {maturity}, height {height()}', flush=True); time.sleep(15)
    step('16-claim-default-loan-2', 'lender', 'pwn_loan_demo.aleo::claim_default', [witness2, lender_salt[2] + 'field'],
         fee_record=fee_change('14-claim-default-early'))
    check('lender claims collateral after maturity without borrower', lambda: 'status: 3u8' in mapping('pwn_loan_demo.aleo', 'loans', lid[2]))
    step('17-withdraw-repayment', 'lender', 'pwn_elastic_proposal_demo.aleo::withdraw_repayment',
         [cid[1], t1, lender_salt[1] + 'field', '110000u64'], fee_record=fee_change('16-claim-default-loan-2'))
    check('lender privately withdrew repayment', lambda: mapping('pwn_elastic_proposal_demo.aleo', 'repayments', cid[1]) == '0u64')
    step('18-cancel-commitment-1', 'lender', 'pwn_elastic_proposal_demo.aleo::cancel_commitment',
         [cid[1], t1, lender_salt[1] + 'field', '100000u64'], fee_record=fee_change('17-withdraw-repayment'))
    check('unused 100,000 refunded privately and commitment closed',
          lambda: mapping('pwn_elastic_proposal_demo.aleo', 'closed', cid[1]) == 'true' and mapping('pwn_elastic_proposal_demo.aleo', 'available_credit', cid[1]) == '0u64')


def summary():
    state = load_state()
    steps = []
    for label, e in state['steps'].items():
        audit_path = PUBLIC / label / 'audit.json'
        a = json.loads(audit_path.read_text()) if audit_path.exists() else {}
        steps.append({'label': label, 'actor': e['actor'], 'function': e['function'], 'fee_mode': e['fee_mode'],
                      'status': e['status'], 'transaction_id': e.get('transaction_id'), 'block_height': e.get('block_height'),
                      'fee_microcredits': e.get('fee_microcredits'), 'prove_wall_seconds': e['prepare_wall_seconds'],
                      'lender_address_on_chain': a.get('lender_address_on_chain'), 'borrower_address_on_chain': a.get('borrower_address_on_chain')})
    write(PUBLIC / 'results.json', {'network': 'testnet', 'run': RUN, 'programs': ['pwn_config_demo.aleo', 'pwn_hub_demo.aleo', 'pwn_elastic_proposal_demo.aleo', 'pwn_loan_demo.aleo'],
                                    'lender': ADDR['lender'], 'borrower': ADDR['borrower'], 'generated_at': now(),
                                    'steps': steps, 'checks': state['checks']})
    print(json.dumps({'steps': len(steps), 'checks': len(state['checks'])}))
    # Whole-lifecycle privacy audit over every confirmed receipt, rejected ones included (SEC-02/03 regression).
    audit = subprocess.run([sys.executable, ROOT / 'scripts/lifecycle_privacy_audit.py', PUBLIC], cwd=ROOT)
    if RUN != 'run1':
        assert audit.returncode == 0, 'lifecycle privacy audit found leaks'


if __name__ == '__main__':
    assert CONFIG['network'] == 'testnet'
    summary() if 'summary' in sys.argv[1:] else main()
