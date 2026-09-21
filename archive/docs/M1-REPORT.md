# Milestone 1 — Architecture & feasibility: status against the grant text

> Record of 2026-09-16: single-pair predecessor of the current programs, deployed on the public testnet (sources in `testnet/programs/`). Current design: [MULTITOKEN.md](../../MULTITOKEN.md).

Date: 2026-09-16. Source of the acceptance text: `private-lending-aleo-grant-overview-v2.html` (Milestones, "Milestone 1 feasibility questions", "Known leakage — to be measured in Milestone 1").

**Overall: technically complete on the public Aleo testnet with real proofs and network finalization; formally open on two non-technical items (stakeholder agreement of the interfaces) and one external dependency (USDCx runtime).** The 2026-09-16 security review found one product-level trust issue (SEC-01, issuer powers over escrow — open) and three client-side privacy defects (fixed; re-measured by testnet run 2). See [SECURITY-REVIEW.md](../../SECURITY-REVIEW.md).

## M1 validation criteria

| Grant criterion | Status | Evidence |
| --- | --- | --- |
| Working custody PoC | **PASS — public testnet** | Four programs deployed ([plan](../artifacts/testnet/deploy/plan.json)); private lender credits → proposal escrow → private borrower record; collateral private → loan escrow → private return/claim. 16 accepted transactions, [results.json](../artifacts/testnet/lifecycle/results.json); every owned output decrypts to the expected party and amount ([recovery.json](../artifacts/testnet/lifecycle/recovery.json)). |
| Asynchronous funded commitment demonstrated | **PASS — public testnet** | Lender opened commitment 1 (400,000) once; borrower drew 200,000 without any lender transaction; a second commitment was drawn to zero. Overdraw above `max_draw` fails at proof time with no transaction. Same on devnode with two distinct borrower keys against one commitment. |
| Privacy matrix measured against real transactions | **PASS with one measured leak — see SEC-02** | [privacy-matrix.json](../artifacts/testnet/lifecycle/privacy-matrix.json) built from confirmed transactions re-fetched from the public API. With private fees, neither lender nor borrower address appears in any of the six **accepted** lending flows; only program addresses do. The matrix did not cover the expected-rejected early default claim (step 14): that step paid a **public** fee, and the receipt publishes the lender address next to the full public Loan witness ([privacy-lifecycle-audit.json](../artifacts/testnet/lifecycle/privacy-lifecycle-audit.json), 4 findings). Amounts, terms and IDs are public (see leakage table below). |
| Core data model and program interfaces documented | **PASS** | [INTERFACES.md](../../INTERFACES.md), compiler ABI snapshots in [interfaces/](../../interfaces/), deployed bytecode is the on-chain reference. |
| Core data model and program interfaces agreed | **OPEN — needs a decision, not more code** | Decisions listed in [INTERFACES.md](../../INTERFACES.md) need PWN sign-off. |

## The six feasibility questions

| Question | Answer | Evidence |
| --- | --- | --- |
| Can lender credit be committed once and drawn asynchronously without lender participation? | **Yes.** | Testnet steps 09 → 12/13: draws signed only by the borrower key; commitment budget decremented in finalize. |
| Can custody safely support private → controlled state → private asset flows? | **Yes against unprivileged users; not against the collateral token's admin (SEC-01).** | Escrow balances live under program addresses; refunds, repayments and collateral leave as records owned by the signer. Early default claim was rejected by network finalization (step 14, fee paid, state unchanged); replay/double-settlement covered on devnode (41 checks). Reproduced on devnode: the registry token admin can `burn_public` collateral sitting in the loan escrow; the pooled balance then fails the last borrower's repayment ([results](../artifacts/security-review/devnode/results.json)). Which issuer powers the product accepts is a decision, not code. |
| What is public, private, inferable or linkable in each transition? | **Measured; see table.** | Public: terms, amounts, commitment/loan IDs, maturity, status, fee amount. Private: record contents, owners, salts. Linkable: commitment → loan by ID; funding → use by amount/timing. |
| Does the model work within USDCx compliance and token-registry constraints? | **Token registry: yes, live. USDCx: interface-compatible, runtime untested.** | Collateral used the real testnet `token_registry.aleo` (token registered, minted, locked, released, claimed). USDCx composition compiles against real bytecode ([probe](../../usdcx_composition_probe/src/main.leo)); no USDCx transfer executed — needs a funded USDCx testnet wallet and freeze-list proofs. |
| Can Proposal, Loan and token programs compose within proving and transaction limits? | **Yes.** | `accept` = 4 transitions across 3 programs + fee in one transaction, 258k variables / 198k constraints of a 4.19M limit; deployment fees 22.7 ALEO total. |
| Measured proving and execution times for the main flows? | **Measured on an M-series laptop, Leo 4.4.2, private fees.** | open 32–34 s, accept 41 s, repay 40 s, claim_default 29 s, withdraw 24 s, cancel 26 s; with public fees roughly 40 s less (deployment-time public-fee estimates 9–18 s). Confirmation 1–4 blocks (~3 s/block). Fees 0.005–0.019 ALEO per lending call, 0.108 ALEO for the whole lifecycle. |

## Known-leakage table, measured

| Leak (grant) | Measured on testnet | Mitigation status |
| --- | --- | --- |
| Collateral amount | Public: `collateral_amount` in the public Loan witness and in the token escrow delta. | Not mitigated in V1; normalized denominations remain a design option. |
| Draw amount | Public: `credit_amount` in the witness; `available_credit` delta. | Not mitigated; normalized draw steps possible. |
| Lender address | **Not visible** in any accepted lending transaction with `fee_private`. **Visible** in the rejected early default claim (step 14, public fee) together with loan ID 11, commitment ID 1 and both authorization hashes — a direct lender ↔ loan link (SEC-02). Also visible in the lender's earlier public shielding (16,757 blocks before the open) and in the public-fee setup calls (initialize, hub tags, token admin). | Private fees validated on testnet as the grant asked. Client now refuses a public fee on any lending call regardless of expected outcome. The published link cannot be undone. Remaining exposure: the public shielding transaction and fee amount. |
| Commitment → loan link | Public by construction (`commitment_id` inside the witness in accept/repay/claim). | Diluted only by multiple draws per commitment. |
| Cross-position link via authorization hash | **Measured (SEC-03):** the client reused one lender salt for commitments 1 and 2 and one borrower salt for loans 11 and 12, so both commitments carry the same lender hash and both loans the same borrower hash. With SEC-02 this ties every position to the lender address. | Client fixed: one fresh salt per commitment and per loan; the lifecycle audit fails on any hash reuse. Draws from one commitment stay linked by the public commitment ID by design. |
| Temporal correlation | Borrower: 88 blocks between shielding and accept, 110 since public funding. | Documented, not concealed. |

Additional finding: the public `Terms` input exposes `credit_asset` as an address (`credits.aleo`), and both program escrow addresses appear in futures. These are protocol addresses, not user addresses.

## Security review

[SECURITY-REVIEW.md](../../SECURITY-REVIEW.md): SEC-01 (issuer burn/freeze/pause over escrow) is an open product decision. The client leaks of run 1 (public fee on the rejected claim, reused salts, predictable IDs) are fixed; `python3 scripts/testnet_lifecycle.py run2` repeats the lifecycle on the deployed programs from run-1 private leftovers and must audit with zero findings. The published link from run 1 stays on chain.

## What is still missing for a clean M1 close

0. **Collateral policy (SEC-01)** — decide which issuer powers (burn, freeze, pause, mint) the product tolerates for collateral, and whether V1 needs a token program that actually enforces non-seizable escrow. Must be closed before real deposits.
1. **Interface sign-off** — PWN decisions on the open items in [INTERFACES.md](../../INTERFACES.md) (ID scheme, direct-offer restriction, Config fields such as fee recipient and launch caps, upgrade policy). The grant defines M1 completion as "agreed and documented"; the code side is done.
2. **USDCx at runtime** — a funded USDCx testnet wallet to run one private open/accept/repay/claim with real freeze-list non-inclusion proofs, stale/rotated roots, frozen escrow and pause, observing `ComplianceRecord` and rollback. Locally this is covered with pinned mainnet bytecode (`make security`); on the public network it is answered by compilation only.
3. **Config scope vs. grant text** — the grant's Config lists fee recipient, launch caps and an emergency stop; the PoC has admin/upgrader/zero fee and uses Hub tag revocation as the stop mechanism (verified: revocation blocks new originations, existing loans settle). Decide whether caps/emergency stop are M1 interface items or M2 implementation.
4. **Second independent lender/borrower on testnet** — two borrowers against one commitment was shown on the devnode only; the testnet run used one borrower drawing from two commitments (budget). Cheap to add (~0.05 ALEO) if the reviewer wants it on chain.
5. **Anonymity is not claimed** — the matrix measures disclosure, not anonymity-set size. Amount/timing correlation is real and documented.

## Public references

- Lender/deployer `aleo1l53e5k624kfh0q78phyxzkvvxq54w89jk36emmzvjmxgkhh8cvyq8hp23s`, borrower `aleo1r7z3attydgg54q22cex0c55mmrnw7caacmau37dxx47uhqafrspsnfdwrd` (testnet, no real value).
- Deployed program IDs and transactions: [testnet/README.md](../testnet/README.md), [artifacts/testnet/deploy/](../artifacts/testnet/deploy/).
- Lifecycle transactions and per-step audits: [artifacts/testnet/lifecycle/](../artifacts/testnet/lifecycle/). Reproduce with `python3 scripts/testnet_lifecycle.py` (resumable; needs a funded `.testnet/account.json`).
