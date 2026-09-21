# Design notes before the lending implementation

Inspected 2026-09-15:

- [PWNLoan](https://github.com/PWNDAO/pwn_protocol/blob/v1.5-deployment-changes/src/core/loan/PWNLoan.sol): `create`, `_settleNewLoan`, `repay`, repayment custody and loan settlement. Its product-dependent debt calculation, hooks and funding allowances are not copied.
- [PWNHub](https://github.com/PWNDAO/pwn_protocol/blob/v1.5-deployment-changes/src/core/hub/PWNHub.sol): administrative `(module, tag)` approvals become a hashed key mapping.
- [PWNConfig](https://github.com/PWNDAO/pwn_protocol/blob/v1.5-deployment-changes/src/core/config/PWNConfig.sol): keep only administration and zero fee. No EVM proxy, hooks or metadata URI system.
- [Leo 4 migration](https://docs.aleo.org/build/leo/documentation/guides/migration-3-5-to-4-0/index.html), [VM tests](https://docs.aleo.org/build/leo/documentation/guides/test/index.html), [credits transfers](https://docs.aleo.org/learn/core-concepts/credits-and-transfers/index.html).
- Actual testnet `credits.aleo`, `token_registry.aleo`, and `test_usdcx_stablecoin.aleo` bytecode. See provenance and hashes below.

| EVM concept | Aleo choice |
| --- | --- |
| allowance / transferFrom while lender is absent | lender spends its own private record once into program-owned public balance |
| contract receives and spends tokens | public balances debited using **immediate caller program**, not transaction signer |
| contract holding a private record | avoided: programs have no signing key for spending such records |
| Solidity sequential state reads before transfers | private execution constructs outputs; authoritative mapping checks run in public finalization |
| previously read available balance | never trusted; subtract from latest mapping at finalization |
| lender/borrower address in storage | domain-separated salted address hashes; private signer proofs for withdrawal/settlement |
| admin authorization | immediate caller (a signer check is phishable through any program the admin signs through) |
| timestamp maturity | block-height maturity computed at acceptance finalization; duration is blocks; interest per block; repayment open until the lender claims |
| arbitrary ERC-20 assets | fixed real credits program plus registry collateral ID; unsupported authorization-gated tokens rejected |
| repayment sent to online lender | allocation in proposal repayment mapping; later private withdrawal by lender |
| deleting settled loan | retained status/hash/maturity tombstone prevents ID replay |

The first custody experiment (`custody_probe`) passed before the loan implementation was written. It uses registry mint, private-to-public and public-to-private bytecode. Initial deployment of the unmodified old registry failed because new deployments now require a constructor. The local variant adds only a non-upgradeable constructor. This is a compatibility adaptation, **not validation of the deployed registry on testnet**.

## Source provenance

Downloaded with the Provable testnet API on 2026-09-15:

- `https://api.explorer.provable.com/v1/testnet/program/credits.aleo` → `vendor/credits.network.aleo`
- `https://api.explorer.provable.com/v1/testnet/program/token_registry.aleo` (edition 1) → `vendor/token_registry.network.aleo`
- Same registry plus appended `constructor: assert.eq edition 0u16;` → `vendor/token_registry.local.aleo`
- `https://api.explorer.provable.com/v1/testnet/program/test_usdcx_stablecoin.aleo` → `research/test_usdcx_stablecoin.aleo`
- `https://api.explorer.provable.com/v1/testnet/program/test_usdcx_freezelist.aleo` → `research/test_usdcx_freezelist.json`

`SHA256SUMS.json` pins the inspected bytecode. These are bytecode snapshots, not tokens redeployed to testnet. The native `credits.aleo` implementation is supplied by snarkVM on the devnode. Local dependencies prevent silently replacing the pinned registry with a mock or a newer network edition.

## USDCx observations from actual bytecode

USDCx is a separate token program; it does **not** call `token_registry.aleo` in this snapshot. Imports are `merkle_tree.aleo`, `test_usdcx_multisig_core.aleo`, and `test_usdcx_freezelist.aleo`.

- `transfer_private_to_public(recipient public, amount public, Token record, [MerkleProof; 2] private)` checks sender non-inclusion, root freshness, pause state, and public recipient freeze status. It returns a compliance record, change Token, and future.
- `transfer_public_to_private(recipient private, amount public)` debits `self.caller`; finalization checks the caller against the freeze mapping and the pause flag. It returns a compliance record, Token, and future. The private recipient is not passed to finalization in this snapshot.
- The current root is key `1u8`; previous root `2u8` is accepted only within the block window. Old proofs can expire between proving and inclusion.
- A compliance record reveals sender, recipient, amount to the designated compliance-record owner. This is not secrecy from the compliance operator.
- An escrow address being frozen or the token being paused prevents settlement regardless of PWN status. A production design must account for this liveness constraint; cannot bypass it in PWN.
- The private deposit has four top-level arguments, with the two Merkle proofs packed into one array. No conclusion about full USDCx loan proving limits follows merely from that argument count.

No freeze-list proof, USDCx transfer, regulated-asset settlement, or USDCx circuit composition has been executed by this PoC. Source inspection supports a candidate integration; it does not establish operational compatibility.

## Additional exact-interface compilation

`usdcx_composition_probe` successfully compiles against the unmodified USDCx, freeze-list, multisig and Merkle snapshots. It retains the actual two-proof array and compliance outputs and composes USDCx public-to-private with a real registry collateral deposit. This is a compile check only; it has no loan authorization and is never deployed/funded. USDCx and freeze-list constructors/initializers bind the token team's deployer address; the multisig dependency has its own deployment authority. No such authorization checks were modified.
