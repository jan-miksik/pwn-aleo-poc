import credits.aleo;
import token_registry.aleo;

// Disposable local experiment: withdrawal deliberately permissionless.
program custody_probe.aleo {
    fn deposit(input: token_registry.aleo::Token, public amount: u128)
        -> (token_registry.aleo::Token, Final) {
        let (change, f) = token_registry.aleo::transfer_private_to_public(std::ctx::addr(), amount, input);
        return (change, final { f.run(); });
    }
    fn withdraw(public asset: field, recipient: address, public amount: u128)
        -> (token_registry.aleo::Token, Final) {
        let (output, f) = token_registry.aleo::transfer_public_to_private(asset, recipient, amount, false);
        return (output, final { f.run(); });
    }
    @noupgrade
    constructor() {}
}
