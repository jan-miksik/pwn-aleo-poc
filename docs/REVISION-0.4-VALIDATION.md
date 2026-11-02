# Revision 0.4 implementation and validation

Validated locally on 2 November 2026 with Leo 4.4.2 (`f3578da`).

## Delivered

- Lender and borrower offers both allow multiple fills. Public offers can serve
  different counterparties; private offers bind one counterparty who can fill
  repeatedly. Every fill creates an independent loan.
- Borrower collateral is partitioned into unused reservations and active loans.
  Repayment rights belong to each accepting lender. Cancellation refunds only
  unused escrow; settlement does not replenish capacity.
- Private commitments bind terms, recipient, taker, direction, visibility and
  module. Privacy documentation includes rejected-transaction disclosures and
  the off-chain opening needed to accept a public borrower offer.
- Administrative asset admission is removed. Module authorization, exact token
  descriptors, reserve accounting and transfer-delta checks remain.
- Repayment remains possible after maturity until the lender's claim settles.
- The Python harness covers the new interfaces. The SDK, app, encrypted delivery,
  private-fee UX and recovery remain grant deliverables.
- The grant copy and matching PDF retain the original section structure and
  three tables, with updated offer, settlement and privacy text. The title is
  "Grant Proposal: Private Lending on Aleo"; SCALE names the grant programme.
  The $85,000 / 17-week milestones are unchanged.

## Checks

| Reproduction command | Result |
| --- | --- |
| `make build` | All four programs compile |
| `make compatibility` | Four ABI/storage/constructor snapshots and 64 finalizers match the intentional 0.4 baseline |
| `make unit` | 24 tests pass |
| `make fuzz` | 189 arithmetic cases pass; seed 20260920 |
| `make test` | 101 checks pass across all 25 pinned asset pairs |
| `make invariants` | 161 checks pass; deterministic prefix and 30 randomized lender-lifecycle actions |
| `make offers` | 392 checks pass; all nine family pairs in both borrower visibility modes and private lender mode |
| `make security` | 189 checks pass; authorization, privacy disclosure, issuer failures, module routing and timelocked upgrades |
| `make allowance` | 15 checks pass; separate optional public-USDCx funding experiment |

`make check` runs all baseline suites sequentially. The verification run also
used isolated temporary copies for independent suites; their generator/test
source hashes were checked before collecting results. Reports, transactions and
fixture provenance are under `artifacts/multitoken/` and are git-ignored.

The arithmetic suite exercises real Leo VM arithmetic. The lifecycle suites use
disposable devnodes and published development keys. Selected acceptance and
repayment cases generate real execution proofs; node verification, deployment
certificates and consensus are disabled. These results are not proof-enabled
public-network validation or an external audit.

The [allowance result](../research/funding-at-acceptance.md) demonstrates atomic
public USDCx funding and native collateral at acceptance, including rollback on
revocation and insufficient balance. Its refund is test cleanup, not production
loan settlement. Funded offers remain the baseline.

## Deployment boundary

Revision 0.4 changes ABI and state layout and requires fresh deployments. It is
not an upgrade or migration of historical testnet positions. No production SDK,
wallet app, public-network deployment or mainnet funding was performed.

Before production, complete proof-enabled testnet and live issuer integration,
encrypted sharing/recovery, private-fee wallet flows, the deficit policy, audit
and immutable deployment. See [SECURITY-REVIEW.md](../SECURITY-REVIEW.md).

The proposal is saved in the
[Google Doc](https://docs.google.com/document/d/1U5hCfMvDNpywJMmi3pvsk516FKDVI3JKPX0qUmsEmls/edit),
with [HTML source](grant-submission.html) and [submission PDF](grant-submission.pdf)
in this directory. The application itself has not been submitted.
