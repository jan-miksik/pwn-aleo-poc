# Real token bytecode snapshots

See `../research/SEMANTICS.md` and `../research/SHA256SUMS.json` for origin.

The lending project statically imports `credits.network.aleo` and `token_registry.local.aleo`. The local registry differs from `token_registry.network.aleo` only by the appended constructor required for new local deployments. All transfer, mint, supply, balance and external-authorization logic is retained unchanged.

This is **not** a custom mint/transfer mock. Test collateral is minted using the actual registry's administrator-controlled mint, as a new test token with no economic value. The test token has `external_authorization_required = false`; regulated registry assets are unsupported.

Do not deploy the local registry variant to a public network. Use the existing network registry for testnet work and resolve editions/record compatibility separately.
