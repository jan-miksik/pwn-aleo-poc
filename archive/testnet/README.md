# Public Aleo testnet connection

Configured and verified on 2026-09-15 using Leo 4.4.2. First real transactions were broadcast the same day (see [Fee privacy](#fee-privacy)).

- Network: `testnet`
- CLI/RPC endpoint: `https://api.explorer.provable.com/v1`
- Additional data API: `https://api.explorer.provable.com/v2`
- Native credit program: `credits.aleo`
- USDCx: `test_usdcx_stablecoin.aleo`
- Freeze list: `test_usdcx_freezelist.aleo`

This is a live API/CLI connection. It does not run a full validator or imply that the lending programs have been deployed to testnet.

## Commands

From the repository root:

```sh
python3 scripts/testnet.py status
python3 scripts/testnet.py address
./scripts/leo query block --latest-height \
  --network testnet \
  --endpoint https://api.explorer.provable.com/v1
```

`python3 scripts/testnet.py init` creates a fresh random account on the first run and reuses it thereafter. It does not use a deterministic seed or the published local-devnode account. Status reads live blocks, public balances, the token pause flag and the current freeze root. Missing public mapping values mean no public balance entry; private records are not scanned. This provider does not expose the devnode-style `consensus_version` route, so status explicitly leaves that value unavailable.

Public connection evidence: [connection.json](../artifacts/testnet/connection.json) and [Leo height query](../artifacts/testnet/leo-height.json). These are snapshots, not a monitor.

## Account and funding

Public address:

```text
aleo1l53e5k624kfh0q78phyxzkvvxq54w89jk36emmzvjmxgkhh8cvyq8hp23s
```

Public metadata is in `account.public.json`. The private key is stored only in `.testnet/account.json` at the repository root; the directory is mode `0700`, the file is mode `0600`, and `.testnet/` is Git-ignored. Key output was captured locally and not written to logs. No key has been imported into a browser extension or sent to the API/faucet. Account files are local plaintext protected by filesystem permissions, not an encrypted keystore.

The account was funded by the project owner with 10 ALEO (10,000,000 microcredits) on 2026-09-15; the arrival was confirmed through the public `credits.aleo/account` mapping. After the private-fee experiment below the public balance is 7,995,392 microcredits (2,000,000 shielded, 4,608 in public fees). USDCx funding is still empty. No faucet request was successfully submitted: in the in-app browser, the faucet did not retain the entered address and its Request Tokens button remained disabled.

- [Official Aleo faucet](https://faucet.aleo.org/) supplies development/test tokens. Enter the public address above. This can require human interaction with its verification flow.
- USDCx funding is separate: use a funded testnet account or the documented [testnet USDCx bridge](https://docs.aleo.org/build/common-uses/usdcx_bridge/index.html). This setup did not create or execute an Ethereum/ARC bridge integration.
- Re-run `status` after funding. For private deliveries, an authorized local record scan is required; public balances alone cannot show private holdings.

## Deploying the lending PoC (done 2026-09-16)

The deployed programs are the single-pair predecessor of the current `_poc` design; the bootstrap admin is the deployer account above. A multisig replaces it through `set_admin` for a more official deployment. The programs are `@noupgrade`: once a name is deployed it is spent for good. The `_poc` design in the repo root is newer and not deployed.

`testnet/programs/*_demo` are the exact sources of the deployed, immutable programs (IDs/imports/hardcoded module references renamed, deployer as bootstrap, `credits.aleo` and `token_registry.aleo` as real network dependencies). They are kept verbatim as the on-chain reference; the generator that produced them was removed with the original devnode sources. `testnet/programs/pwn_test_utils` computes authority hashes offline for the lifecycle client and is never deployed. The current multi-token programs in the repo root are not deployed anywhere.

`scripts/deploy_testnet.py` mirrors the fee experiment: `prepare` builds against the live testnet dependencies and generates the four proved deployment transactions with certificates locally (63 s), `inspect` writes [plan.json](../artifacts/testnet/deploy/plan.json), `submit <program>` broadcasts one saved transaction in dependency order and refuses to re-broadcast, `confirm <program>` records acceptance.

| Program | Size | Deployment fee |
| --- | ---: | ---: |
| `pwn_config_demo.aleo` | 1.2 KB | 3.28 ALEO |
| `pwn_hub_demo.aleo` | 0.8 KB | 2.26 ALEO |
| `pwn_elastic_proposal_demo.aleo` | 6.8 KB | 9.80 ALEO |
| `pwn_loan_demo.aleo` | 4.6 KB | 7.36 ALEO |
| **Total** | | **22.70 ALEO** |

Fees are dominated by transaction storage (~1.07 ALEO/KB) plus 1 ALEO namespace fee per program; they were paid publicly by the deployer after the project owner topped the account up to 26.995 ALEO. All four deployments were accepted in blocks 19653434–19653445 ([confirmations](../artifacts/testnet/deploy/)).

### Lifecycle on testnet

`python3 scripts/testnet_lifecycle.py` ran the full lifecycle with real proofs (resumable: confirmed steps and passed checks are skipped on rerun; nothing is ever re-broadcast). A second random account (`borrower.public.json`) acts as borrower. Collateral is a fresh test token on the live `token_registry.aleo`. The six lending flows pay private fees from records shielded beforehand; setup calls pay public fees.

| # | Step | Actor | Fee | Result | Prove |
| --- | --- | --- | --- | --- | ---: |
| 01–03 | initialize, hub approvals | lender/admin | public | accepted | 9–10 s |
| 04, 06 | register_token, mint_private (live registry) | lender/admin | public | accepted | 11–12 s |
| 05, 07, 08 | fund borrower, borrower shields two records | both | public | accepted | 10–13 s |
| 09, 10 | open_commitment 400,000 and 300,000 | lender | private | accepted, no address | 32–34 s |
| 11 | accept 350,000 > max_draw | borrower | — | fails at proof time, no tx | 9 s |
| 12, 13 | accept 200,000 / 300,000 | borrower | private | accepted, no address | 41 s |
| 14 | claim_default before maturity | lender | public | **rejected by finalization**, fee paid — **privacy leak**: public fee payer + rejected execution publish the lender address next to the Loan witness ([SEC-02](../../SECURITY-REVIEW.md)) | 18 s |
| 15 | repay loan 1 (220,000) | borrower | private | accepted, no address | 40 s |
| 16 | claim_default loan 2 after maturity | lender | private | accepted, no address | 29 s |
| 17, 18 | withdraw_repayment 220,000, cancel unused 200,000 | lender | private | accepted, no address | 24–26 s |

Evidence: [results.json](../artifacts/testnet/lifecycle/results.json), per-step `audit.json`/`transaction.json`, [privacy-matrix.json](../artifacts/testnet/lifecycle/privacy-matrix.json), [recovery.json](../artifacts/testnet/lifecycle/recovery.json). Public balance after everything: 2.773 ALEO.

Whole-run privacy audit (every confirmed receipt, rejected included): `python3 scripts/lifecycle_privacy_audit.py artifacts/testnet/lifecycle` → 4 findings (step 14 public fee + lender address; lender hash shared by commitments 1 and 2; borrower hash shared by loans 11 and 12), see [privacy-lifecycle-audit.json](../artifacts/testnet/lifecycle/privacy-lifecycle-audit.json) and [SECURITY-REVIEW.md](../../SECURITY-REVIEW.md). The script now refuses a public fee on any lending call and uses one salt per position and random IDs.

### Run 2 (after the security review)

`python3 scripts/testnet_lifecycle.py run2` repeats steps 09–18 on the same deployed programs with the fixed client: private fee on the expected-rejected claim, a fresh salt per commitment and per loan, random commitment/loan IDs (`artifacts/testnet/lifecycle-run2/ids.json`). It needs no setup steps and no new shielding: every input is a private record left over from run 1 (lender 220,000 + 200,000 credits and the fee-change chain; borrower 300,000 + 250,000 collateral, 280,000 credits and its fee-change chain), so no public transaction names a participant near the lending calls. Draws are 100,000 each; loan 1 lasts 400 blocks, loan 2 20 blocks. State and secrets go to `.testnet/lifecycle-run2/`, public receipts to `artifacts/testnet/lifecycle-run2/`; the run ends by asserting that the whole-run audit has zero findings. Grant mapping: [M1-REPORT.md](../docs/M1-REPORT.md).

## Fee privacy

A public fee includes the payer's address in the publicly observable transaction data. In the local lending tests, the payer is the lender/borrower, so the fee links that address to the operation even when token records are encrypted. This reveals a blockchain address; identifying its real-world owner requires other information.

Aleo also supports private fees paid from a private credits record and independently sponsored fees. These remove or change that particular fee-payer link, but do not hide the public proposal terms, loan IDs or escrow amounts. [Official fee documentation](https://docs.aleo.org/learn/core-concepts/transactions/index.html).

### Private-fee experiment on public testnet (2026-09-15, PASS)

Three real, fully proved `credits.aleo` transactions were broadcast from the account above and accepted by the network. They were prepared, inspected, broadcast and confirmed as separate steps by `scripts/private_fee_testnet.py`; the private key never left `.testnet/`.

| Step | Function | Fee | Transaction | Block | Payer address visible in confirmed transaction |
| --- | --- | --- | --- | ---: | --- |
| shield-fee | `transfer_public_to_private` 1 ALEO | `fee_public` 2,304 µALEO | `at1y24spcvs5m0lxn7f6vu52muyyzep25prh40q52r764m3g4effv9qjfekl6` | — | **yes** (execution argument and fee payer) |
| shield-transfer | `transfer_public_to_private` 1 ALEO | `fee_public` 2,304 µALEO | `at1pduf8ugznd2hw9vvapm4fa9j03t89ff7wduljh9xgc88w5gyj5pq009muw` | — | **yes** |
| private-transfer | `transfer_private` 0.1 ALEO to self, fee from the second record | `fee_private` 2,308 µALEO | `at18z9e36dwmxfwqhjw85hwzz6t9asgzg2pgk48ymgvdypejsp5xspslpdzvx` | 19636875 | **no** — zero `aleo1…` strings anywhere in the confirmed transaction |

The last row was re-fetched from the public API after confirmation, not from local files: [chain-audit.json](../artifacts/testnet/private-fee/chain-audit.json). Its only public values are the fee amount, the `0u64` priority fee and the deployment/execution ID field; execution inputs are `record, private, private` and fee inputs are `record, public, public, public`. All three record outputs (received transfer, transfer change, fee change) decrypt locally to the payer ([recovery.json](../artifacts/testnet/private-fee/private-transfer/recovery.json); plaintext amounts stay in `.testnet/`). Proving `transfer_private` plus `fee_private` took 49.4 s wall time on this machine versus 8.9 s for the public-fee shielding steps ([audit.json](../artifacts/testnet/private-fee/private-transfer/audit.json)).

What this does and does not show:

- A transaction paid with `fee_private` publishes no payer address. The lender/borrower link created by public fees in the local tests is removable.
- The shielding step that creates the fee record is itself public and names the address. An observer sees that this address shielded 1 ALEO twice; it cannot link either record to the later private spend without the view key (spends publish serial numbers, not commitments). Amount and timing correlation remains possible, as noted in [PRIVACY.md](../../PRIVACY.md).
- Fee amounts stay public, and `transfer_private` is a native-credits call. The same fee mode was applied to the six PWN lending flows on the local devnode ([privacy-audit-private-fees.json](../artifacts/privacy-audit-private-fees.json)); it has not yet been exercised with the lending programs on testnet because they are not deployed there.

Rerun or extend (each step is idempotent and never re-proves or re-broadcasts an existing transaction):

```sh
python3 scripts/private_fee_testnet.py prepare shield-fee      # then submit, confirm
python3 scripts/private_fee_testnet.py prepare shield-transfer # then submit, confirm
python3 scripts/private_fee_testnet.py prepare private-transfer
python3 scripts/private_fee_testnet.py submit private-transfer
python3 scripts/private_fee_testnet.py confirm private-transfer
python3 scripts/private_fee_testnet.py recover private-transfer
```
