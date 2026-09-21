# Interfaces and decisions pending PWN agreement

Data model, entry points and ABI: [MULTITOKEN.md](MULTITOKEN.md) and the
compiler snapshots in [interfaces/](interfaces/).

Implemented and tested is not agreed. Status becomes **agreed** only after
explicit acceptance by PWN.

1. **Funding model.** Lender funds public escrow once; acceptance and repayment
   never need the lender online. Repayments accumulate for private withdrawal
   and do not reopen draw capacity.
2. **Disclosure.** Terms, amounts, IDs and commitment→loan relations are public;
   participant identity privacy depends on private fees, fresh salts and wallet
   behaviour, not on the contracts.
3. **Timing.** Duration in blocks. Repayment is allowed while the loan is active,
   also after maturity, until the lender's claim finalizes; first finalized wins.
   Interest accrues per block at a nominal 10 s/block.
4. **Term bounds.** duration 10 … 3,153,600 blocks, APR ≤ 100,000 bps, ratios
   ≤ 1,000,000 bps, native repayment incl. scheduled interest ≤ u64. Confirm the
   product values.
5. **Exits survive administration.** Cancel/expiry/delisting/module pause never
   block repayment, claim, withdrawal or cancellation of existing positions.
6. **Asset admission.** Admin registers a token once per family/version;
   supported profiles are native, ARC-20 with `balances`, and the deployed
   USDCx/USAD ABI. New profiles = new versioned entry points.
7. **Governance.** Caller-checked admin, two-step handover, per-edition upgrade
   timelock. Decide the production delay, a multisig admin and final program
   names (short names carry a namespace premium).
8. **Issuer powers (SEC-01, open).** Which burn/freeze/pause powers are tolerated
   for credit and collateral, whitelist in contracts vs. SDK, and the deficit
   rule. Must be closed before real deposits.
9. **IDs.** Derived from the participant's authorization hash and a nonce;
   nobody can pre-occupy another account's ID.
10. **Not in scope of the PoC.** Refund of repayment surplus, partial repayment,
    price liquidation, decimals conversion, salt recovery, fee recipient / launch
    caps / emergency stop beyond module tag revocation.
