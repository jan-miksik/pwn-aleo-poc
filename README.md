# PWN private fixed-term loan — Aleo PoC

Leo 4.4.2. One lender funds an Elastic Proposal once; borrowers draw
independently; fixed-term repayment or default. Native ALEO, ARC-20 and the
deployed USDCx/USAD compliance ABI in either role. No frontend, SDK,
installments, pooling or oracle.

Programs: `pwn_config_poc`, `pwn_hub_poc`, `pwn_loan_poc` (the loan core) and
`pwn_proposal_poc` (the Elastic Proposal offer module) — generated, local devnode
only; the `_poc` suffix is interim — shorter names carry a namespace premium.
Design: [MULTITOKEN.md](MULTITOKEN.md).

The core imports no offer module. It calls the module named in each loan through
the `OfferModule` interface (Leo dynamic dispatch), and the Hub decides which
modules may originate loans. A new offer type is a new program plus one
`set_offer_module` transaction; the core stays unchanged.

```mermaid
flowchart TD
    C[pwn_config_poc: admin, timelocked upgrades] --> H[pwn_hub_poc: module tags + asset registry]
    H --> P[pwn_proposal_poc: offer module, credit escrow]
    H --> L[pwn_loan_poc: loan core, collateral escrow]
    A[Lender private record] -->|open| P
    B[Borrower private collateral] -->|accept| L
    L -->|draw via OfferModule@name| P
    P -->|private credit| B
    B -->|repay until lender claims| L
    L -->|collateral back| B
    L -->|claim at/after maturity| A
    P -->|cancel unused / withdraw repayments| A
```

Programs own **public** balances; nested calls debit the immediate caller
program. Private records always belong to a person.

## Run

```sh
make setup      # pinned Leo 4.4.2 into .tools/leo
make build      # regenerate + compile
make check      # unit, compatibility, fuzz, test, invariants, security
```

Individual suites and scope: [docs/TESTING.md](docs/TESTING.md). Generated
`pwn_*/src/main.leo` must not be edited by hand.

## Lifecycle

1. Admin: `initialize`, `set_offer_module` per offer module, `set_tag` for the loan core, `set_asset` per token.
2. Lender: `open_<family>(nonce, terms, record, amount, salt)` → escrow.
3. Borrower: `accept_<credit>_<collateral>(nonce, offer_module, commitment, loan_terms, collateral, salt)` → collateral locked, private credit delivered atomically. The module checks `loan_terms` against its offer.
4. Borrower: `repay_<credit>_<collateral>` while the loan is active (also after maturity, until the lender claims) → collateral back.
5. Lender: `claim_<collateral>` at/after maturity; `withdraw_<family>` repayments; `cancel_<family>` unused credit.

Use a fresh random salt per position and private fees.

## Documents

- [MULTITOKEN.md](MULTITOKEN.md) — design, families, terms, reserve guard, governance, tests
- [SECURITY-REVIEW.md](SECURITY-REVIEW.md) — what holds, open risks (SEC-01 issuer powers)
- [INTERFACES.md](INTERFACES.md) — decisions pending PWN agreement
- [PRIVACY.md](PRIVACY.md) — disclosure matrix, salts, fees
- [archive/](archive/README.md) — Milestone 1 material from the single-pair predecessor (public-testnet deployment, reports, scripts, artifacts); not maintained
- [research/](research/SEMANTICS.md), [vendor/README.md](vendor/README.md) — semantics notes, token bytecode provenance

`custody_probe`, `usdcx_composition_probe`, `artifacts/token-dispatch-probe`: compile-only experiments, never funded.

## License

GPL-3.0-only, see [LICENSE](LICENSE).
