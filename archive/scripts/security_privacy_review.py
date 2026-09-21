#!/usr/bin/env python3
"""Read-only verification of privacy links in saved public testnet receipts.

Never reads .testnet secrets, contacts the network, or submits transactions.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/testnet/lifecycle'


def inspect(label):
    path = BASE / label / 'transaction.json'
    raw = path.read_bytes()
    receipt = json.loads(raw)
    tx = receipt['transaction']
    execution = tx.get('execution') or receipt.get('rejected', {}).get('execution')
    assert execution, label
    public = '\n'.join(str(value.get('value', ''))
                       for transition in execution['transitions']
                       for value in transition['inputs'] + transition['outputs']
                       if value['type'] in ('public', 'future'))
    return {
        'file': str(path.relative_to(ROOT)),
        'sha256': hashlib.sha256(raw).hexdigest(),
        'status': receipt['status'],
        'transaction_id': tx['id'],
        'fee_function': tx['fee']['transition']['function'],
        'fee_addresses': sorted(set(re.findall(r'aleo1[a-z0-9]{58}', json.dumps(tx['fee'])))),
        'lender_auth': sorted(set(re.findall(r'lender_auth:\s*(\d+field)', public))),
        'borrower_auth': sorted(set(re.findall(r'borrower_auth:\s*(\d+field)', public))),
        'loan_ids': sorted(set(re.findall(r'loan_id:\s*(\d+field)', public))),
        'commitment_ids': sorted(set(re.findall(r'commitment_id:\s*(\d+field)', public))),
        'rejected_execution_visible': bool(receipt.get('rejected', {}).get('execution')),
    }


def main():
    labels = ['09-open-commitment-1', '10-open-commitment-2',
              '12-accept-loan-1', '13-accept-loan-2', '14-claim-default-early']
    evidence = [inspect(label) for label in labels]
    lender = json.loads((ROOT / 'testnet/account.public.json').read_text())['address']
    rejected = evidence[-1]
    assert rejected['status'] == 'rejected' and rejected['fee_function'] == 'fee_public'
    assert lender in rejected['fee_addresses'] and rejected['rejected_execution_visible']
    assert all(e['lender_auth'] == rejected['lender_auth'] and e['lender_auth'] for e in evidence)
    assert evidence[2]['loan_ids'] == rejected['loan_ids']
    assert evidence[2]['borrower_auth'] == evidence[3]['borrower_auth'] and evidence[2]['borrower_auth']
    report = {
        'scope': 'Saved public receipts only; not re-fetched from the network during this review.',
        'checks': {
            'rejected_claim_links_known_lender_fee_address_to_loan': True,
            'lender_auth_reused_across_two_commitments': True,
            'borrower_auth_reused_across_two_loans': True,
        },
        'evidence': evidence,
    }
    out = ROOT / 'artifacts/security-review/privacy-links.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: 3 privacy-link checks reproduced from saved public receipts.')


if __name__ == '__main__':
    main()
