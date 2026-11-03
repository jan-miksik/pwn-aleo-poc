# Security status

Revision 0.4 adds bidirectional multiple fills and private offer commitments.
It is a local PoC, not an externally audited production release. Historical
September 2026 reviews cover the earlier implementation, not these changes.

## Invariants and regression coverage

- Offer escrow accepts draws/repayments only from the exact core as immediate
  caller. The Hub authorizes new originations; revocation does not block exits.
- Borrower pending collateral plus active collateral equals core liabilities,
  per asset. A fill reclassifies collateral without creating or releasing reserves.
- Every borrower fill binds a distinct lender, witness hash and loan ID. Repayment
  credit and withdrawal authorization are per loan, never per borrower offer.
- Cancel refunds unused collateral only. Per-loan upward rounding cannot allocate
  another loan's reserve; an unfillable remainder remains refundable.
- Private openings bind mode, taker, recipient, terms, module and salt. Taker
  possession of an opening does not grant maker withdrawal rights.
- Loan hashes include direction. Changing direction, lender rights or settlement
  terms invalidates the witness. Settlement is allowed once.
- Both asset descriptors are checked without a registry. Exact token routes,
  reserve guards and transfer deltas remain enforced.
- Administration uses immediate caller checks, two-step transfer and delayed
  upgrades. Loans repay until a successful default claim, including after maturity.

Actual test and proof/verification scope is in [docs/TESTING.md](docs/TESTING.md).
Source inspection is not an audit guarantee.

## Remaining production risks

**SEC-01 — issuer powers and deficits.** Burn, freeze, pause or upgrades can affect
all positions held in a token. Reserve guards block outgoing payouts if backing
is insufficient; the code does not allocate losses or repair deficits. Incoming
repayments remain possible where the token allows them. Define the production
deficit policy before real deposits. No administrative asset admission is added.

**Untrusted token code.** ABI compatibility and reported balance deltas do not
prove legitimacy. A malicious program may lie about balances or include unexpected
nested calls. An SDK/wallet must inspect the complete authorized execution,
including signer-debiting calls, and display exact program identity. Removing
asset admission does not sandbox token code.

**Privacy and availability.** Public borrower acceptance needs an off-chain
opening; counterparties see payout details. Active economics and offer-to-loan
links are public. The harness uses public fees. Encrypted delivery, backups,
private fees and proving privacy remain production integration requirements.

**Governance and token upgrades.** PoC upgrades can change protections despite
the 720-block delay. The grant targets an immutable audited core; token issuers
can still change their programs. A pinned interface cannot guarantee that an
issuer preserves settlement compatibility.

Other retained limits: stale compliance proofs can reject transfers; repayment
surplus goes to the lender; lost salts have no on-chain recovery; effective APR
depends on actual block time. The allowance probe has a test-only refund and
no repayment/default economics; it must never be used as a real loan.
