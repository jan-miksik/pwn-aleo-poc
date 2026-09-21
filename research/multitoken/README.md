# Mainnet snapshots for multi-token integration

Retrieved from `https://api.provable.com/v2/mainnet/program/{program_id}` on
2026-09-17. Original instruction text, with a final newline, is pinned here;
SHA256SUMS.json hashes these files. These are code snapshots, not ledger state.
SOL and WBTC are separate real ARC-20 implementations; USDCx and USAD retain
their actual compliance logic. No network endpoint is called by the local tests.

Local bootstrap adaptations are made only in generated staging copies by
`scripts/multitoken_workspace.py`, with a per-line provenance report. The shared
merkle-tree bytecode is the existing `research/merkle_tree.aleo` fixture.
