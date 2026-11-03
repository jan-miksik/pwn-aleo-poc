# Token snapshot provenance

Revision 0.4 uses `credits.network.aleo` for native interface compilation and
the pinned ARC-20 and USDCx/USAD programs in
[research/multitoken](../research/multitoken/README.md). The devnode supplies native
credits. Other token fixtures retain their operational transfer and compliance
instructions; `scripts/multitoken_workspace.py` changes only local bootstrap
authorities or adds a constructor, with a per-line provenance report. Tokens
minted in the disposable local ledger have no economic value.

The registry snapshots in this directory belong to the historical single-pair
implementation. `token_registry.local.aleo` differs from its network snapshot
only by an appended non-upgradeable constructor. Their original provenance is
in [SEMANTICS.md](../research/SEMANTICS.md) and
[SHA256SUMS.json](../research/SHA256SUMS.json). The current core does not use that
registry for asset admission.

Do not deploy local bootstrap variants to a public network. Live integration
must resolve the issuer's current program edition, record ABI and authorization.
