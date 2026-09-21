# Privacy and linkability

Amounts are not hidden. The protocol keeps participant addresses out of its
public state and delivers tokens as private records. No anonymity-set size or
traffic-analysis resistance is measured. The on-chain measurements come from the
Milestone 1 testnet run of the single-pair predecessor ([archive/](archive/README.md));
the model is unchanged.

| Operation | Public | Private | Linkable |
| --- | --- | --- | --- |
| open | commitment ID, terms, amount, lender hash, escrow delta | input/change records, salt | fee payer (if public), shielding by amount/time |
| accept | loan ID, commitment ID, terms, amounts, both hashes, maturity, both token calls | collateral record, salt, delivered credit | commitment → loan by ID |
| repay / claim | full loan witness, amounts, status change | records, salt, recipient | loan → commitment → open |
| cancel / withdraw | commitment ID, terms, lender hash, amount, escrow delta | salt, payout record | prior positions |

Token futures expose program and amount, not private owners. Transition IDs,
record commitments/serials and transaction grouping are observable.

## Authorization hashes

`BHP256({domain, protocol, account: signer, salt})`. Borrowers need the lender's
hash, not the address. The hash carries no position ID, so a **reused salt is a
persistent pseudonym** across positions — use one fresh random salt per
commitment and per loan (client enforces; audit fails on reuse). A lost salt
strands the position. Fixture salts are public and give no privacy.

## Fees and rejected transactions

A public fee names the payer. A **rejected** execution is published beside its
fee transaction, witness included, so it leaks the same way — testnet run 1
paid a public fee on the expected-rejected early claim and linked the lender to
both commitments and both loans (still on chain; [M1 report](archive/docs/M1-REPORT.md)).
The client now requires `fee_private` on every lending call. With private fees
none of the six lending flows contains a participant address, on devnode
([privacy-audit-private-fees.json](archive/artifacts/privacy-audit-private-fees.json))
and on testnet ([privacy-matrix.json](archive/artifacts/testnet/lifecycle/privacy-matrix.json),
[chain-audit.json](archive/artifacts/testnet/private-fee/chain-audit.json)). Remaining
exposure: fee amount, the public shielding that funded the fee record, and
amount/timing correlation between shielding and lending.

## USDCx

The compliant token emits `ComplianceRecord` (sender, recipient, amount) to its
compliance account; private deposits carry two freeze-list non-inclusion
proofs and the root reaches finalization. Privacy from users is not privacy
from that operator; a frozen escrow or paused token blocks settlement.
