#!/usr/bin/env python3
"""Resumable public-testnet deployment of the `_demo` lending programs.

prepare: generate deployment transactions (certificates, real proofs) locally; no broadcast.
inspect: summarize cost, program IDs and fee visibility from the saved transactions.
submit <program>: broadcast one saved deployment (dependencies first); refuses to re-broadcast.
confirm <program>: check acceptance and record block metadata.
"""
import argparse, json, os, subprocess, time, urllib.error, urllib.request
from pathlib import Path
from testnet import ROOT, CONFIG, SECRET, now

LOCAL = ROOT / '.testnet/deploy'
PUBLIC = ROOT / 'artifacts/testnet/deploy'
PROGRAMS = ['pwn_config_demo', 'pwn_hub_demo', 'pwn_elastic_proposal_demo', 'pwn_loan_demo']
ENTRY = ROOT / 'testnet/programs/pwn_loan_demo'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def rpc(path, body=None):
    req = urllib.request.Request(CONFIG['endpoint'] + '/testnet/' + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={'Content-Type': 'application/json', 'User-Agent': 'pwn-aleo-poc'})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def saved(program):
    return LOCAL / (program + '.aleo.deployment.json')


def prepare(_):
    if any(saved(p).exists() for p in PROGRAMS):
        print('Saved deployment transactions exist; delete .testnet/deploy to regenerate. Nothing broadcast.')
        return inspect(_)
    subprocess.run(['python3', str(ROOT / 'scripts/testnet_programs.py')], check=True, cwd=ROOT)
    LOCAL.mkdir(parents=True, exist_ok=True, mode=0o700)
    wallet = json.loads(SECRET.read_text())
    env = dict(os.environ, PRIVATE_KEY=wallet['private_key'], NETWORK='testnet', ENDPOINT=CONFIG['endpoint'])
    for name in ('DEVNET', 'CONSENSUS_VERSION', 'CONSENSUS_HEIGHTS'):
        env.pop(name, None)
    args = [str(ROOT / 'scripts/leo'), 'deploy', '--path', str(ENTRY), '--network', 'testnet',
            '--endpoint', CONFIG['endpoint'], '--save', str(LOCAL), '--yes',
            '--json-output=' + str(LOCAL / 'result.json')]
    started, clock = now(), time.perf_counter()
    print('Generating deployment transactions locally (no broadcast) ...', flush=True)
    with (LOCAL / 'leo.log').open('w') as log:
        proc = subprocess.run(args, env=env, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    write(LOCAL / 'timing.json', {'started_at': started, 'prepare_wall_seconds': round(time.perf_counter() - clock, 3), 'exit_code': proc.returncode})
    if proc.returncode:
        raise SystemExit('Deployment preparation failed; see .testnet/deploy/leo.log (redact before sharing).')
    inspect(_)


def inspect(_):
    address = json.loads(SECRET.read_text())['address']
    result = json.loads((LOCAL / 'result.json').read_text())
    stats = {d['program_id']: d['stats'] for d in result['deployments']}
    report, total = [], 0
    for program in PROGRAMS:
        path, pid = saved(program), program + '.aleo'
        if not path.exists():
            report.append({'program': pid, 'saved': False}); continue
        tx = json.loads(path.read_text())
        dep, fee, cost = tx['deployment'], tx['fee']['transition'], stats[pid]
        assert pid in dep['program'].split('\n', 2)[-1][:200] or f'program {pid};' in dep['program'], 'Program ID mismatch'
        assert tx['type'] == 'deploy' and tx['fee'].get('proof'), 'Not a proved deployment transaction'
        total += cost['total_cost']
        report.append({'program': pid, 'saved': True, 'transaction_id': tx['id'], 'edition': dep.get('edition'),
            'program_size_bytes': cost['program_size_bytes'], 'functions_certified': len(dep['verifying_keys']),
            'fee_function': fee['function'], 'payer_address_in_fee': address in json.dumps(fee),
            'cost_microcredits': {k: cost[k] for k in ('storage_cost', 'synthesis_cost', 'namespace_cost', 'constructor_cost', 'total_cost')},
            'per_call_execution_cost_microcredits': {f['name']: f['execution_cost'] for f in cost['function_costs']}})
    balance = rpc(f'program/credits.aleo/mapping/account/{address}')
    summary = {'checked_at': now(), 'network': 'testnet', 'deployer': address,
               'consensus_version': result['config']['consensus_version'],
               'total_fee_microcredits': total, 'total_fee_aleo': total / 1_000_000,
               'public_balance_microcredits': balance, 'funding_sufficient': int(balance.rstrip('u64')) >= total,
               'programs': report, **json.loads((LOCAL / 'timing.json').read_text()),
               'note': 'Deployment fees are paid publicly by the deployer; nothing broadcast by prepare/inspect.'}
    write(PUBLIC / 'plan.json', summary)
    print(json.dumps(summary, indent=2))


def submit(program):
    index = PROGRAMS.index(program)
    for dependency in PROGRAMS[:index]:
        receipt = PUBLIC / dependency / 'confirmation.json'
        assert receipt.exists() and json.loads(receipt.read_text())['status'] == 'accepted', f'{dependency} must be accepted first'
    attempt_path = PUBLIC / program / 'submission.json'
    if attempt_path.exists():
        print('Submission already attempted; checking receipt instead of re-broadcasting.')
        return confirm(program)
    tx = json.loads(saved(program).read_text())
    attempt = {'transaction_id': tx['id'], 'submitted_at': now(), 'outcome': 'pending_or_uncertain'}
    write(attempt_path, attempt)
    response = rpc('transaction/broadcast', tx)
    attempt.update(outcome='broadcast_response_received', response=response)
    write(attempt_path, attempt)
    print(json.dumps(attempt, indent=2))


def confirm(program):
    txid = json.loads(saved(program).read_text())['id']
    try:
        receipt = rpc('transaction/confirmed/' + txid)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            print('Not yet confirmed: ' + txid); return False
        raise
    assert receipt.get('status') in ('accepted', 'rejected')
    write(PUBLIC / program / 'confirmation.json', receipt)
    block_hash = rpc('find/blockHash/' + txid)
    meta = rpc('block/' + block_hash)['header']['metadata']
    checked = {'program': program + '.aleo', 'transaction_id': txid, 'status': receipt['status'],
               'block_hash': block_hash, 'block_height': meta['height'], 'block_timestamp': meta['timestamp'],
               'program_visible_on_chain': bool(rpc('program/' + program + '.aleo')), 'confirmed_checked_at': now()}
    write(PUBLIC / program / 'confirmation-metadata.json', checked)
    print(json.dumps(checked, indent=2))
    if receipt['status'] != 'accepted':
        raise SystemExit('Deployment rejected; diagnose before continuing.')
    return True


if __name__ == '__main__':
    os.umask(0o077)
    assert CONFIG['network'] == 'testnet' and json.loads(SECRET.read_text())['network'] == 'testnet'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'inspect', 'submit', 'confirm'))
    parser.add_argument('program', nargs='?', choices=PROGRAMS)
    a = parser.parse_args()
    if a.command in ('submit', 'confirm') and not a.program:
        parser.error('program required')
    globals()[a.command](a.program)
