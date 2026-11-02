# Funding at acceptance — local feasibility result

Verified 2 November 2026 with the repository's pinned Leo 4.4.2 toolchain.

**Result:** a borrower-signed execution can lock native ALEO collateral and draw
public USDCx from a lender's prior allowance atomically. Posting the quote and
approving the spender do not transfer principal or collateral. This is an
optional public-funding path, separate from the funded-offer baseline.

## Evidence

The pinned [USDCx bytecode](multitoken/usdcx_stablecoin.aleo) exposes
`approve_public`, `unapprove_public` and `transfer_from_public_to_private`.
The transfer hashes `{account: lender, spender: self.caller}`, checks the lender's
freeze status and token pause flag, then decrements both allowance and public
balance. It creates a private borrower token and an issuer compliance record.
[Snapshot origin and hashes](multitoken/README.md) identify the inspected edition.

`make allowance` stages the isolated
[probe](../scripts/multitoken_allowance_probe.py), using those operational token
instructions unchanged. Only local deployment/initialization authorities are
adapted; the staging directory records each adaptation in
`fixture-provenance.json`.

The run passed 15 assertions across 36 attempted transactions. It checked:

- Posting and approval leave the lender's public balance and collateral reserve
  unchanged.
- The borrower supplies its own private collateral record; the committed quote
  fixes the lender, borrower, amounts and expiry.
- Acceptance transfers 400 USDCx base units and locks 600 native microcredits in
  one execution. The output decrypts to the correct owner and amount.
- Revoked allowance and insufficient lender balance reject acceptance without
  retaining collateral or accepted-loan state. The same collateral record remains
  usable for the successful attempt.
- Wrong signer, modified quote, replay, cancellation and expired authorization
  reject.

The successful acceptance generated a real execution proof. The local devnode
did **not** verify execution proofs or deployment certificates and ran no
consensus. This demonstrates local composition and rollback, not a verified
public-network deployment or live issuer integration. The probe's borrower refund
is test cleanup; it has no repayment/default economics and is not a real loan.

## Why this does not replace all funded offers

The inspected VM requires the same signer across an execution's transitions and
checks that a consumed private record belongs to that signer. Ordinary nested
calls therefore cannot combine independently owned lender and borrower private
records merely by sharing two signatures. See the pinned
[execution verifier](https://github.com/ProvableHQ/snarkVM/blob/c2909c55efb0c2202e7471e3e2efd73de1c4a468/synthesizer/process/src/verify_execution/mod.rs#L261)
and [record ownership check](https://github.com/ProvableHQ/snarkVM/blob/c2909c55efb0c2202e7471e3e2efd73de1c4a468/circuit/program/src/request/verify.rs#L300).

The allowance path avoids consuming a lender-owned private record. It works for
the tested public USDCx funding route while the borrower signs the final execution
and provides its own collateral. It does not establish asynchronous, lender-only
acceptance of an unfunded borrower offer holding native collateral. Native private
collateral still needs borrower authorization at execution, or earlier escrow.

Public allowances expose the funding account and amount, reserve no funds, and
can be revoked or exhausted. Freeze/pause and issuer upgrade risks remain.
Encrypted offer sharing cannot hide that funding trail. Extending the probe to
production also requires quote capacity, per-loan accounting, settlement,
front-running protection through bound terms, wallet execution review, and
proof-enabled public-network tests.

## Proposal decision

Keep both lender and borrower baseline offers funded at posting. Retain the
allowance route as an M1 feasibility/integration deliverable, with the public
funding disclosure and unavailable-balance handling stated explicitly. No
production program imports the experimental probe.
