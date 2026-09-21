# Testing

```sh
make unit            # generator, harness and invariant-oracle regressions (stdlib only)
make compatibility   # build + compare ABI, storage, constructors, 43 finalizers with tests/fixtures/multitoken-compatibility.json
make fuzz            # 89 fixed boundaries + 100 seeded cases in the real Leo VM
make invariants      # deterministic prefix + 30 randomized lifecycle actions
make test            # 25 asset-pair lifecycle matrix
make security        # adversarial suite, incl. real-proof substitution case
make check           # all of the above

make fuzz SEED=42 FUZZ_CASES=1000
make invariants SEED=42 STEPS=100
python3 scripts/multitoken_fuzz.py --seed 20260920 --cases 100 --case 40
```

Devnode suites bind a loopback port, use public dev keys and a shared staged
workspace — run them one at a time. Reports: `artifacts/multitoken/<suite>/results.json`.

## Sources and compatibility gate

`scripts/generate_multitoken.py` renders token-specific entry points (signatures,
transfers, compliance outputs, reserve reads); `scripts/multitoken_logic.py`
holds shared validation/accounting helpers rendered into the same programs. The
entry points keep the order: validate → reserve precondition → state update →
token finalizers → reserve delta postcondition.

`tests/fixtures/multitoken-compatibility.json` fingerprints ABIs, storage,
constructors and every finalizer. It changes only with a reviewed protocol
change (`check_multitoken_compatibility.py --update`); a refactor must pass it
unchanged.

## Fuzz

`multitoken_fuzz.py` compiles the same `MATH` fragment the generator embeds and
compares it with Python's unbounded integers: `ceil(amount × ratio / 10⁴)`,
`floor(principal × apr × elapsed / 315,360,000,000)` with `elapsed = blocks × 10`,
u64 narrowing. Each case needs the exact result or a recognized arithmetic
failure (snarkVM overflow panics count, other panics fail). Logs per case under
`artifacts/multitoken/fuzz/seed-<seed>/`.

## Invariants

`multitoken_invariants.py` keeps an event model and compares it with devnode
mappings after every action, including rejected ones:

1. proposal liabilities per asset = Σ available credit + unwithdrawn repayments;
2. loan liabilities per collateral = Σ collateral of active loans;
3. reserve = liabilities + known donations (a donation creates no entitlement);
4. per-position amounts/flags match; closed commitments still let loans repay;
5. witness hash, start, maturity, terms hash, asset descriptor immutable; status only
   active → repaid/defaulted; no second payout; active loans repay at any height,
   claims need maturity;
6. rejected operations change nothing, even after one nested finalizer ran;
7. private outputs decrypt for the intended recipient with the expected amount.

`trace.json` is written before each action for replay. Scenarios use APR 0;
nonzero interest is covered by fuzz and the security suite.

## Negative tests

`multitoken_test_support.py` distinguishes accepted transactions, VM instruction
failures, finalize rejections and record-inclusion failures; compiler warnings,
CLI help or connection errors never count as a passed negative test. The
substitution case requires the node's "commitment does not exist" diagnostic
and keeps a genuine-proof control.

## Scope

Local devnode: no proof verification (except the stated cases), no deployment
certificates, no consensus. Coverage is counted in scenarios and assertions, not
lines. Not covered: proof-enabled public-network validation, browser/SDK
proving, live USDCx freeze-list operation, real block-time APR calibration.
