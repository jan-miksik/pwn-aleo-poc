# Multi-token lending — revision 0.4

Canonical source: `scripts/generate_multitoken.py` (entry-point plumbing),
`scripts/multitoken_logic.py` (existing lending logic), and
`scripts/multitoken_offers.py` (commitments and borrower reservations).
Never edit generated `pwn_*/src/main.leo` directly. Fresh local deployments only;
new schemas are incompatible with old positions.

## Token profiles

| Family | Suffix | Required profile, version 1 |
| --- | --- | --- |
| 1 | `aleo` | Native `credits.aleo`, u64 transfers |
| 2 | `arc20` | Private/public transfers and `balances[address]: u128` |
| 3 | `compliant` | Pinned USDCx/USAD ABI, two Merkle proofs with 16 siblings, compliance outputs, u128 balances |

`Asset = {program_id, token_id, family, version}`. Both descriptors are validated:
family 1–3, version 1, token_id zero, and native iff the program is `credits`.
There is no asset registry or admission transaction. New compatible programs need
no core redeployment. Matching an ABI does not make an arbitrary token trustworthy.
Other balance layouts, NFTs, rebasing and fee-on-transfer behavior are unsupported.

## Interfaces

The Hub still authorizes offer modules and the core; it does not authorize tokens.
The core has no static module import. It calls the chosen module dynamically:

- `draw_<family>(id, loan_terms, offer_witness, recipient)` pays lender-offer credit.
- `receive_<family>(loan_witness, input, amount[, proofs])` credits repayment.
  It uses the offer ID for lender offers and the loan ID for borrower offers.

Loan witnesses include `borrower_offer` in their hash. The original `LoanTerms`
contains assets, principal/collateral, base repayment, APR, duration and lender
authorization. Shared types exported by the Hub are:

- `OfferTerms`: direction (1 lender / 2 borrower), assets, per-fill min/max,
  collateral/repayment ratios, APR, duration, expiry and maker authorization.
- `OfferOpening`: recipient, designated taker, and fresh commitment salt.
- `OfferWitness`: terms, opening, and private/public mode.
- `BorrowFunding`: total requested principal and collateral deposited.

Private-mode constraints in proof code are explicitly predicated: a helper
containing assertions can execute eagerly even when called inside a conditional.
Finalizers branch between public mapped terms and private commitment validation.

## Lender offers

Public `open_<family>` retains the original public `Terms` layout with
`lender_auth`. Private `open_private_<family>` uses shared terms and an opening.
Each escrows credit in the offer module. `accept_<credit>_<collateral>` in the core
takes an `OfferWitness`, locks the accepting borrower's collateral and calls
`draw`. Public lender acceptance uses the canonical empty witness with mode false;
private acceptance supplies the actual committed witness.

The module validates all economics and the private taker where applicable.
Each fill creates a separate loan. `cancel_<family>` / `cancel_private_<family>`
refund exactly unused credit and close the offer. `withdraw_<family>` /
`withdraw_private_<family>` withdraw accumulated repayment. Capacity never revolves.

## Borrower offers

`open_borrow_<collateral>` takes a public listing, private `OfferWitness`,
collateral record, funding totals and borrower ownership salt. For public mode
the listing must equal the terms; for private mode it must be the canonical empty
terms. This keeps both modes in the same entry point under Leo's 31-function limit.

Collateral is held by the core. Mappings track commitment, optional public terms,
expiry, remaining requested principal, unused collateral and closure. Acceptance
also needs the off-chain opening: public terms alone do not reveal the recipient
or commitment salt. Once the maker has supplied the opening, they can be offline.

`accept_borrow_<credit>` takes the committed witness and lender credit. It:

1. verifies mode, designated taker where private, fill limits, exact assets and commitment;
2. creates a unique ID bound to the core, module, offer, borrower/lender authorities and nonce;
3. subtracts principal capacity and the upward-rounded collateral needed by this loan;
4. reclassifies pending collateral as active without changing total collateral liabilities;
5. transfers lender credit through transient core custody to the committed borrower.

Funding and delivery each have exact balance-delta checks. Failure rolls back
both transfers and all state. The borrower needs no private record in this execution.
Two fills can have different lenders, maturities and outcomes.

`cancel_borrow_<collateral>` authenticates the maker and opening, closes unused
capacity and refunds exactly unused collateral. It works after expiry or complete
funding and never releases active collateral. Repaid collateral is returned to
the borrower, not automatically offered again.

## Repayment and default

Both directions share `repay_<credit>_<collateral>` and `claim_<collateral>`.
For borrower offers, the module stores repayment and witness hash by loan ID;
`withdraw_loan_<credit>` requires that loan's lender authorization. Neither the
borrower maker nor a sibling lender can withdraw it.

Repayment is allowed while active, including at or after maturity. Claims require
height >= maturity. The first successful settlement wins. Maturity starts at each
fill and is unrelated to offer expiry. Module revocation cannot block old exits.

## Amounts and capacity

| Parameter | Bound |
| --- | --- |
| Per-fill min/max | u128, 0 < min <= max |
| Collateral ratio | 1 … 1,000,000 bps |
| Base repayment ratio | 10,000 … 1,000,000 bps |
| APR | <= 100,000 bps |
| Duration | 10 … 3,153,600 blocks |
| Native transfers | Checked u64 narrowing; native scheduled repayment bounded at posting |

Collateral and base repayment use `ceil(principal * ratio / 10000)` per loan.
Interest remains `floor(principal * apr * blocks * 10 / 315360000000)`.
The nominal block time is 10 seconds; surplus repayment belongs to the lender.

A borrower deposits at least `ceil(requested * collateral_ratio / 10000)`.
Independent upward rounding can make many small fills require more than that
aggregate minimum. Remaining requested principal is a cap, not guaranteed
fillable liquidity. Every fill must also fit available collateral; clients must
check both. Below-minimum principal and insufficient-collateral remainders can be
cancelled/refunded. There is no minimum-fill exception or automatic top-up.

## Reserve and governance invariants

- Module liabilities = unfilled lender credit + lender-offer repayments +
  unwithdrawn per-loan borrower-offer repayments, by token.
- Core liabilities = pending borrower collateral + active loan collateral, by token.
- Outgoing transfers/new exposure require full backing; every token movement checks
  its observed delta. Incoming repayment can replenish a deficient credit reserve.
- Donations create no entitlement. Issuer-induced deficits block outgoing payments
  but do not define a loss allocation policy; other tokens remain isolated.
- Administration checks immediate caller, uses two-step handover and a 720-block
  per-edition upgrade delay. Upgrades remain a PoC capability, not production immutability.

Compiled snapshots are in `interfaces/`; the intentional revision is captured by
the compatibility fixture. See [docs/TESTING.md](docs/TESTING.md) for validation,
[PRIVACY.md](PRIVACY.md) for disclosures and [SECURITY-REVIEW.md](SECURITY-REVIEW.md)
for remaining production risks.
