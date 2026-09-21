import test_usdcx_stablecoin.aleo;
import token_registry.aleo;

// COMPILE-ONLY EXPERIMENT. No loan authorization. Never fund/deploy this probe.
// All stablecoin/freezelist/multisig/Merkle bytecode imports are unmodified.
program usdcx_composition_probe.aleo {
    fn deposit(input: test_usdcx_stablecoin.aleo::Token, public amount: u128,
        proofs: [test_usdcx_stablecoin.aleo::MerkleProof; 2])
        -> (test_usdcx_stablecoin.aleo::ComplianceRecord, test_usdcx_stablecoin.aleo::Token, Final) {
        let (compliance, change, f) = test_usdcx_stablecoin.aleo::transfer_private_to_public(std::ctx::addr(), amount, input, proofs);
        return (compliance, change, final { f.run(); });
    }

    fn cross_asset_draw(public credit_amount: u128,
        collateral: token_registry.aleo::Token, public collateral_amount: u128)
        -> (test_usdcx_stablecoin.aleo::ComplianceRecord, test_usdcx_stablecoin.aleo::Token, token_registry.aleo::Token, Final) {
        let (change, lock) = token_registry.aleo::transfer_private_to_public(std::ctx::addr(), collateral_amount, collateral);
        let (compliance, credit, payout) = test_usdcx_stablecoin.aleo::transfer_public_to_private(std::ctx::signer(), credit_amount);
        return (compliance, credit, change, final { lock.run(); payout.run(); });
    }
    @noupgrade
    constructor() {}
}
