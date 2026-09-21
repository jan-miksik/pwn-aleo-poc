#!/usr/bin/env python3
"""Resumable, real-proof native-credits private-fee experiment on public testnet.

Secrets and plaintext records stay in .testnet/. Saved transactions are proved
once, inspected, and broadcast separately. Never use development keys here.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

from testnet import ROOT, CONFIG, SECRET, now

LOCAL = ROOT / '.testnet/private-fee'
PUBLIC = ROOT / 'artifacts/testnet/private-fee'
LABELS = ('shield-fee', 'shield-transfer', 'private-transfer')


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def rpc(path, body=None):
    req = urllib.request.Request(CONFIG['endpoint'] + '/testnet/' + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={'Content-Type': 'application/json', 'User-Agent': 'pwn-aleo-poc'})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.load(response)


def paths(label):
    local = LOCAL / label
    public = PUBLIC / label
    local.mkdir(parents=True, exist_ok=True, mode=0o700)
    public.mkdir(parents=True, exist_ok=True)
    return local, public


def transaction(label):
    local, _ = paths(label)
    return json.loads((local / 'transaction.execution.json').read_text())


def prepare(label):
    local, public = paths(label)
    if (local / 'transaction.execution.json').exists():
        print('Saved transaction already exists; use inspect/submit/confirm. No new proof generated.')
        inspect(label)
        return
    wallet = json.loads(SECRET.read_text())
    env = dict(os.environ, PRIVATE_KEY=wallet['private_key'], NETWORK='testnet', ENDPOINT=CONFIG['endpoint'])
    for name in ('DEVNET', 'CONSENSUS_VERSION', 'CONSENSUS_HEIGHTS'):
        env.pop(name, None)
    if label.startswith('shield-'):
        function = 'transfer_public_to_private'
        inputs = [wallet['address'], '1000000u64']
        fee = []
    else:
        for previous in LABELS[:2]:
            _, evidence = paths(previous)
            receipt = json.loads((evidence / 'confirmation.json').read_text())
            if receipt.get('status') != 'accepted':
                raise SystemExit('Both shielding transactions must be confirmed accepted.')
        function = 'transfer_private'
        # Ciphertext inputs prevent plaintext record data from appearing in argv.
        inputs = [transaction('shield-transfer')['execution']['transitions'][0]['outputs'][0]['value'],
                  wallet['address'], '100000u64']
        fee = ['--fee-records', transaction('shield-fee')['execution']['transitions'][0]['outputs'][0]['value']]
    args = [str(ROOT/'scripts/leo'), 'execute', 'credits.aleo::' + function, *inputs, *fee,
        '--path', str(ROOT/'testnet/programs/pwn_test_utils'), '--network', 'testnet',
        '--endpoint', CONFIG['endpoint'], '--save', str(local), '--yes',
        '--json-output=' + str(local/'result.json')]
    started = now()
    clock = time.perf_counter()
    print('Generating real execution and fee proofs: ' + label, flush=True)
    with (local/'leo.log').open('w') as output:
        proc = subprocess.run(args, env=env, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
    elapsed = round(time.perf_counter() - clock, 3)
    write(local/'timing.json', {'started_at': started, 'prepare_wall_seconds': elapsed, 'exit_code': proc.returncode})
    if proc.returncode or not (local/'transaction.execution.json').exists():
        raise SystemExit('Preparation failed. Inspect local log after redacting secrets; no broadcast requested.')
    inspect(label)


def inspect(label):
    local, public = paths(label)
    tx = transaction(label)
    result = json.loads((local/'result.json').read_text())
    address = json.loads(SECRET.read_text())['address']
    fee = tx['fee']['transition']
    execution = tx['execution']['transitions']
    expected = 'fee_private' if label == 'private-transfer' else 'fee_public'
    assert fee['function'] == expected, 'Unexpected fee visibility'
    assert tx['execution'].get('proof') and tx['fee'].get('proof'), 'Missing real proof'
    assert all(t['program'] == 'credits.aleo' for t in execution), 'Unexpected program'
    cost = result['stats']['total_cost']
    # Experiment safety budget: at most 0.1 ALEO per transaction, three total.
    assert 0 < cost <= 100_000, 'Fee exceeds experiment cap'
    if label == 'private-transfer':
        assert address not in json.dumps(tx), 'Private transaction exposes wallet address'
        assert execution[0]['function'] == 'transfer_private'
        assert [i['type'] for i in execution[0]['inputs']] == ['record', 'private', 'private']
        assert not any(o['type'] == 'future' for t in [*execution, fee] for o in t['outputs'])
    report = {
        'checked_at': now(), 'network': 'testnet', 'label': label,
        'transaction_id': tx['id'], 'function': execution[0]['function'],
        'fee_function': fee['function'], 'fee_microcredits': cost,
        'consensus_version': result['config']['consensus_version'],
        'execution_proof_present': bool(tx['execution']['proof']),
        'fee_proof_present': bool(tx['fee']['proof']),
        'payer_address_in_serialized_transaction': address in json.dumps(tx),
        'payer_address_in_fee': address in json.dumps(fee),
        'execution_inputs': [i['type'] for i in execution[0]['inputs']],
        'fee_inputs': [i['type'] for i in fee['inputs']],
        **json.loads((local/'timing.json').read_text()),
        'timing_note': 'Whole Leo prepare command, including fetching, synthesis and proofs; excludes broadcast/confirmation.',
    }
    # Only ciphertext/chain-visible data and a whitelisted summary leave .testnet.
    write(public/'transaction.json', tx)
    write(public/'audit.json', report)
    print(json.dumps(report, indent=2))


def confirm(label):
    _, public = paths(label)
    txid = transaction(label)['id']
    try:
        receipt = rpc('transaction/confirmed/' + txid)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            print('Not yet confirmed: ' + txid)
            return False
        raise
    assert isinstance(receipt, dict) and receipt.get('status') in ('accepted', 'rejected'), 'Unexpected receipt format'
    write(public/'confirmation.json', receipt)
    checked = {'transaction_id': txid, 'status': receipt['status'], 'confirmed_checked_at': now()}
    block_hash = rpc('find/blockHash/' + txid)
    block = rpc('block/' + block_hash)
    metadata = block['header']['metadata']
    checked.update(block_hash=block_hash, block_height=metadata['height'], block_timestamp=metadata['timestamp'])
    submitted = json.loads((public/'submission.json').read_text())
    from datetime import datetime
    checked['submission_to_block_seconds'] = round(metadata['timestamp'] - datetime.fromisoformat(submitted['submitted_at']).timestamp(), 3)
    write(public/'confirmation-metadata.json', checked)
    print(json.dumps(checked, indent=2))
    if receipt['status'] != 'accepted':
        raise SystemExit('Transaction rejected; stop and diagnose before doing anything further.')
    return True


def recover(label):
    """Locally decrypt owned outputs, including fee change; never print records."""
    local, public = paths(label)
    assert json.loads((public/'confirmation.json').read_text())['status'] == 'accepted'
    tx = transaction(label)
    address = json.loads(SECRET.read_text())['address']
    transitions = [*tx['execution']['transitions'], tx['fee']['transition']]
    outputs = [(t['function'], o) for t in transitions for o in t['outputs'] if o['type'] == 'record']
    recovered = []
    with tempfile.NamedTemporaryFile(mode='w', dir=LOCAL, prefix='key-', delete=True) as keyfile:
        keyfile.write(json.loads(SECRET.read_text())['private_key'])
        keyfile.flush()
        for index, (function, output) in enumerate(outputs):
            # `leo account decrypt` prints the plaintext record; it does not honour --json-output.
            args = [str(ROOT/'scripts/leo'), 'account', 'decrypt', '-f', keyfile.name,
                '--ciphertext', output['value'], '--network', 'testnet', '--disable-update-check']
            proc = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
            (local/f'decrypted-{index}.txt').write_text(proc.stdout)
            assert proc.returncode == 0 and f'owner: {address}.private' in proc.stdout, 'Local output decryption failed'
            recovered.append({'transition': function, 'output_index': index, 'decrypts_to_owner': True})
    # Amounts stay local: the public summary only states that every record output is ours.
    summary = {'label': label, 'checked_at': now(), 'record_outputs': len(outputs),
        'all_record_outputs_owned_by_payer': True, 'records': recovered,
        'plaintext_location': str(local.relative_to(ROOT))}
    write(public/'recovery.json', summary)
    print(json.dumps(summary, indent=2))


def submit(label):
    local, public = paths(label)
    inspect(label)
    if (public/'submission.json').exists():
        print('Submission already attempted; checking receipt without creating/broadcasting a new transaction.')
        confirm(label)
        return
    # Persist attempt before network I/O: uncertain failures cannot lead to a new tx.
    attempt = {'transaction_id': transaction(label)['id'], 'submitted_at': now(), 'outcome': 'pending_or_uncertain'}
    write(public/'submission.json', attempt)
    result = rpc('transaction/broadcast', transaction(label))
    attempt.update(outcome='broadcast_response_received', response=result)
    write(public/'submission.json', attempt)
    print(json.dumps(attempt, indent=2))


if __name__ == '__main__':
    os.umask(0o077)
    assert CONFIG['network'] == 'testnet' and CONFIG['endpoint'] == 'https://api.explorer.provable.com/v1'
    assert json.loads(SECRET.read_text())['network'] == 'testnet'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'inspect', 'submit', 'confirm', 'recover'))
    parser.add_argument('label', choices=LABELS)
    args = parser.parse_args()
    globals()[args.command](args.label)
