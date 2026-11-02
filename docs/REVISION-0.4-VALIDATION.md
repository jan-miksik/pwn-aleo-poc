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
- The full grant proposal has been revised and edited to 2,790 words. Its
  substantive sections, 24 section headings, seven tables (104 cells) and three
  corrected diagrams are retained. The title is "Grant Proposal: Private
  Lending on Aleo"; SCALE names the grant programme. The $85,000 / 17-week
  milestones are unchanged. The restored original is preserved. The designated
  revised document, HTML and native Google Docs PDF are synchronized; see below.

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

## Proposal preservation and verification

The revision uses the full original proposal and retains its substantive
sections, 24 section headings, seven tables and three diagrams. Its table shapes
are 2×3, 6×3, 7×2, 6×3, 6×2, 4×3 and 6×4, totaling 104 cells. The full source body has SHA-256
`9851c28ba5543cc4c9d110b22ee5f35ee05e044409cbd0b4b7cb4add2ae1a3db`.

The [original document](https://docs.google.com/document/d/1pGR4fng2Mpj6cYE0aJZ9U-lE5wCBXe88NlC_UzJsSRc/edit)
is restored and was left unchanged during the editorial revision. HTML and
native DOCX exports verify all 183 original text blocks, seven native tables,
three embedded diagrams and an empty footer. All three figures were visually
checked in its 11-page PDF during restoration; the final check confirms the
original text and embedded image contents are unchanged.

The [designated revised document](https://docs.google.com/document/d/1U5hCfMvDNpywJMmi3pvsk516FKDVI3JKPX0qUmsEmls/edit)
was updated in place and renamed "Grant Proposal: Private Lending on Aleo".
Its 181 content blocks match the [HTML source](grant-submission.html). The
editorial pass reduces the previous 3,566 words to 2,790 and the overview to
259 words. It consolidates repeated qualifications, removes speculative salary
and invoice products, places integration targets in Collaborative Value, and
keeps token safeguards and disclosures in Asset Scope and Privacy Model.
Implementation commitments remain in the corresponding milestones. Market
context and the M2 heading are named consistently. All 42 hyperlinks and the
table dimensions are retained.

Native DOCX verification confirms seven tables with bold, repeating first-row
headers, 25 headings including the title kept with their following content,
three nonempty embedded diagrams and an empty footer.

The [submission PDF](grant-submission.pdf) is the final native Google Docs
export. All 181 content blocks are present across its 11 pages, with no blank
page. The rendered proposal and final layout corrections were visually checked,
including the lifecycle, architecture and privacy figures on pages 5, 6 and 8.
The embedded figures match the repository assets, allowing for Google Docs'
image resizing.

The proposal describes both offer directions and visibility modes, removes
administrative asset admission while retaining module and token safeguards,
and documents settlement, custody and privacy limits. SCALE identifies the
grant programme. The $85,000 request and 17-week milestone schedule are
unchanged. No additional Google document was created, and the grant application
has not been submitted. Editorial verification was completed on 3 November 2026.
Protocol suites above were completed earlier in this revision; the editorial
update did not change protocol code or APIs, and those suites were not rerun.
