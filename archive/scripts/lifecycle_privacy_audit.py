#!/usr/bin/env python3
"""Privacy audit of a whole testnet lifecycle run from its saved confirmed receipts.

Unlike the six-flow matrix, this reads every confirmed receipt in the run directory,
rejected transactions included: a rejected execution is published beside its fee, so
it leaks exactly like an accepted one. Reads only public artifacts (no .testnet).

    python3 scripts/lifecycle_privacy_audit.py [artifacts/testnet/lifecycle]

Findings (exit 1 when any):
  public_fee_on_lending_flow     lending transition paid with fee_public (SEC-02)
  participant_address_in_lending known lender/borrower address anywhere in a lending receipt
  lender_auth_reused             one lender hash across several commitment IDs (SEC-03)
  borrower_auth_reused           one borrower hash across several loan IDs (SEC-03)
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LENDING = {'open_commitment', 'accept', 'repay', 'claim_default', 'cancel_commitment', 'withdraw_repayment'}
ADDRESS = re.compile(r'aleo1[a-z0-9]{58}')


def main(run_dir):
    run_dir = Path(run_dir)
    participants = {'lender': json.loads((ROOT / 'testnet/account.public.json').read_text())['address'],
                    'borrower': json.loads((ROOT / 'testnet/borrower.public.json').read_text())['address']}
    steps, findings = [], []
    lender_hashes, borrower_hashes = {}, {}   # hash -> set of commitment / loan IDs it was published with
    for path in sorted(run_dir.glob('*/transaction.json')):
        label = path.parent.name
        receipt = json.loads(path.read_text())
        tx = receipt['transaction']
        execution = tx.get('execution') or receipt.get('rejected', {}).get('execution') or {'transitions': []}
        transitions = execution['transitions']
        top = transitions[-1] if transitions else {'program': None, 'function': None, 'inputs': [], 'outputs': []}
        function = top['function']
        lending = function in LENDING and (top['program'] or '').startswith('pwn_')
        public = '\n'.join(str(v.get('value', '')) for t in transitions for v in t['inputs'] + t['outputs']
                           if v['type'] in ('public', 'future'))
        serialized = json.dumps(receipt)
        visible = {k: a in serialized for k, a in participants.items()}
        entry = {'step': label, 'status': receipt['status'], 'transaction_id': tx['id'],
                 'program': top['program'], 'function': function, 'lending_flow': lending,
                 'execution_published': bool(transitions), 'rejected_execution': 'execution' in receipt.get('rejected', {}),
                 'fee_function': tx['fee']['transition']['function'],
                 'fee_payer_addresses': sorted(set(ADDRESS.findall(json.dumps(tx['fee'])))),
                 'lender_address_visible': visible['lender'], 'borrower_address_visible': visible['borrower'],
                 'lender_auth': sorted(set(re.findall(r'lender_auth:\s*(\d+field)', public))),
                 'borrower_auth': sorted(set(re.findall(r'borrower_auth:\s*(\d+field)', public))),
                 'commitment_ids': sorted(set(re.findall(r'commitment_id:\s*(\d+field)', public))),
                 'loan_ids': sorted(set(re.findall(r'loan_id:\s*(\d+field)', public)))}
        if function == 'open_commitment' and transitions:
            # open_commitment(id, terms, ...): the ID is the first public input, the lender hash sits in terms
            entry['commitment_ids'] = [top['inputs'][0]['value']]
        if function == 'accept' and transitions:
            entry['loan_ids'] = [top['inputs'][0]['value']]
        steps.append(entry)
        if not lending:
            continue
        if entry['fee_function'] != 'fee_private':
            findings.append({'finding': 'public_fee_on_lending_flow', 'step': label, 'status': receipt['status'],
                             'fee_payer_addresses': entry['fee_payer_addresses']})
        for who, seen in visible.items():
            if seen:
                findings.append({'finding': 'participant_address_in_lending', 'step': label, 'participant': who})
        for h in entry['lender_auth']:
            lender_hashes.setdefault(h, set()).update(entry['commitment_ids'])
        for h in entry['borrower_auth']:
            borrower_hashes.setdefault(h, set()).update(entry['loan_ids'])
    for h, ids in lender_hashes.items():
        if len(ids) > 1:
            findings.append({'finding': 'lender_auth_reused', 'hash': h, 'commitment_ids': sorted(ids)})
    for h, ids in borrower_hashes.items():
        if len(ids) > 1:
            findings.append({'finding': 'borrower_auth_reused', 'hash': h, 'loan_ids': sorted(ids)})
    report = {'run_dir': str(run_dir.relative_to(ROOT)) if run_dir.is_relative_to(ROOT) else str(run_dir),
              'source': 'saved confirmed receipts (accepted and rejected), not re-fetched',
              'lending_receipts': sum(s['lending_flow'] for s in steps), 'receipts': len(steps),
              'findings': findings, 'steps': steps}
    out = run_dir / 'privacy-lifecycle-audit.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    verdict = 'FAIL' if findings else 'PASS'
    print(f'{verdict}: {len(steps)} receipts, {report["lending_receipts"]} lending, {len(findings)} findings -> {out.relative_to(ROOT)}')
    for f in findings:
        print('  ', json.dumps(f))
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'artifacts/testnet/lifecycle'))
