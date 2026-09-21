# Security status

Reviews on 2026-09-16 and 2026-09-21. Resolved findings are not listed; their
regressions live in `make security` (`artifacts/multitoken/security/results.json`).

## What holds

- Only the hardcoded `pwn_loan_poc` (immediate caller) can draw from or repay
  into the proposal escrow; a hub tag grants no program spending access.
- Lender and borrower are bound by `signer` + secret salt; terms and loan
  witness by hash; position IDs are derived from the account.
- Accounting is isolated per token; the reserve-delta postcondition catches a
  non-conforming token; exits never depend on hub or config.
- Admin functions check the immediate caller, handover is two-step, upgrades are
  timelocked; repayment stays possible until the lender claims; terms are
  bounded; interest accrues per block. Details: [MULTITOKEN.md](MULTITOKEN.md).

Resolved so far: client-side privacy leaks (public fee on rejected calls, salt
reuse, predictable IDs) and contract-side governance, settlement-timing, term
bound and repayment-predictability issues.

## Open

**SEC-01 — token issuer powers (product decision).** An issuer with a
burn/freeze/pause role can hit the escrow; the loss is shared by all positions
in that token and the code does not allocate it. USDCx on mainnet: one ADMIN key
without timelock can grant BURNER, one PAUSER, one FREEZER
(`scripts/usdcx_issuer_powers_check.py`). Decide which powers the product
tolerates, whether the whitelist lives in the contracts or the SDK, and the
deficit rule. Required before real deposits.

**Outside the code:**
1. A token issuer's upgrade (the compliant profile hardcodes the USDCx ABI incl.
   `[field; 16]` proofs) can block positions until PWN upgrades — the timelock
   must not prevent that repair.
2. `UPGRADE_DELAY = 720` blocks and the multisig admin are test / undecided values.
3. A stale freeze-list proof rejects a compliant repayment; the client generates
   proofs right before broadcasting.
4. Repayment surplus goes to the lender (a refund would change the ABI).
5. A lost salt strands the position for its owner; there is no recovery.
6. Effective APR depends on the real block time (nominal 10 s).
