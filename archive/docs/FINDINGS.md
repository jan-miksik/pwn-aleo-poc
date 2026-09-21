# Feasibility findings (2026-09-15, single-pair predecessor)

**GO with architecture changes.** Funded asynchronous custody works with real Aleo
token mechanics on a local devnode and, since 2026-09-16, on the public testnet
([docs/M1-REPORT.md](M1-REPORT.md)). Current design: [MULTITOKEN.md](../../MULTITOKEN.md).

| Question | Result |
| --- | --- |
| A. Fund once, accept later without lender | **PASS** custody; identity privacy only with private fees |
| B. Public escrow → private records | **PASS** for native credits and registry tokens; program balances debited via immediate caller |
| C. Public disclosure | **PARTIAL** — amounts, terms, IDs, commitment→loan public; addresses out of protocol state ([PRIVACY.md](../../PRIVACY.md)) |
| D. Two asset programs in one transaction | **PASS** — `accept` = 4 transitions + fee, real proof generated |
| E. USDCx / token-registry constraints | registry live; USDCx composes against real bytecode, runtime later covered locally (`make security`), public network untested |
| F. Proving performance | measured single-machine samples only |

## Custody model

- Lender's private record → proposal's public balance; only ID, terms hash,
  unused credit and a salted lender hash are stored.
- `accept` locks collateral in the loan program and calls the proposal's
  restricted `draw`, which pays a borrower-owned private record. All checks use
  finalize-time mappings; failure rolls back token and state changes.
- Repayments go to a separate mapping for the lender's private withdrawal; cancel
  returns only unused credit; active loans stay independent.
- Local registry fixture appends only a constructor (required by current
  consensus); transfer logic unchanged.

## Measurements (macOS arm64, Leo 4.4.2, local devnode)

| Flow | With real execution proof | Without proof (median) |
| --- | ---: | ---: |
| `open_commitment` | 162.7 s (first use) | 1.2 s |
| `accept` | 26.1 s | 1.7 s |
| `repay` | 26.5 s | 1.6 s |
| `claim_default` | 13.3 s | 1.3 s |

Circuits: `accept` 82k constraints, `repay` 62k, `claim_default` 54k
([synthesize.log](../artifacts/synthesize.log)). Whole-process wall time; not
isolated prover time, not browser/WASM.

## Still required before production

1. Asset policy for issuer powers (SEC-01) and explicit adapters per token.
2. Private fees, fresh salts, wallet/SDK privacy validation.
3. Full-proof lifecycle on a public network with real tokens; browser/SDK benchmarks.
4. Production administration and upgrade policy (delay, multisig, names).
