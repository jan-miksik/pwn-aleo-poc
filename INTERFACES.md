# Protocol decisions — revision 0.4

Agreed for this implementation: both offer directions support multiple fills;
visibility is independent of direction; there is no administrative asset admission;
repayment stays possible until a default claim settles.

1. **Funding.** A lender deposits credit; a borrower deposits collateral. Each
   acceptance supplies the other asset and creates a separate loan atomically.
   Posting is funded; the optional allowance experiment is not the baseline.
2. **Capacity.** Fill limits are strict, requested principal is a cap, and each
   loan rounds collateral upward. Both principal and collateral remaining must
   cover a borrower fill. Rounding can leave an unfillable, refundable remainder.
   Repayment and recovered collateral do not replenish offers.
3. **Ownership.** Each borrower-offer fill binds the accepting lender. Repayments
   accumulate by loan ID for that lender; they never belong to the borrower maker.
   Existing lender offers retain aggregate withdrawals for their single lender.
4. **Visibility.** Public lender offers retain the `Terms` schema. Private lender
   and borrower offers use shared `OfferTerms` / `OfferOpening` / `OfferWitness`.
   Private offers authorize one designated counterparty, who may fill repeatedly.
   Public borrower acceptance needs an off-chain opening as well as public terms.
5. **Timing.** Duration is in blocks, starting at each acceptance. Loans repay
   while active, including after maturity; claims require maturity. First finalized
   settlement wins. Interest uses the existing nominal 10 seconds per block.
6. **Exits.** Offer expiry, cancellation and module revocation do not block
   settlement of existing loans. Cancellation refunds only unused escrow.
7. **Assets.** Structural validation replaces admission: supported family/version,
   exact program identity, and token_id zero. Native means `credits` only; token
   programs require the implemented transfer/balance ABI. Module approval remains.
8. **Identifiers.** Borrower-fill IDs bind core, module, offer, borrower/lender
   authorization and nonce. The loan witness binds the offer direction and all
   settlement rights. Each opening uses a salt distinct from ownership salts.
9. **Compatibility.** New schemas and call signatures require fresh local
   deployments. Compiled ABIs are in `interfaces/`. No existing-position migration
   or production deployment is performed by this change.

## Production decisions still open

Issuer-induced deficit handling, accepted issuer powers, audit remediation,
wallet integrations, encrypted backup/recovery, production governance and final
program names remain production work. Asset admission is not an open choice:
there is no protocol token whitelist. The PoC's 720-block upgrade delay remains
a test setting; the grant targets an audited immutable core.

Partial repayment of an individual loan, revolving capacity, repayment-surplus
refunds, pooled/crowdfunded debt, oracle liquidation, new token profiles and
confidential active-loan economics are outside this revision.
