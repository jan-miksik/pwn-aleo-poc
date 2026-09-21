interface Arc20 {
    record Token { owner: address, amount: u128, .. }
    fn transfer_private_to_public(input: Token, public recipient: address, public amount: u128) -> (Token, Final);
    view fn balance_of(account: address) -> u128;
}
interface Stable {
    mapping balances: address => u128;
}
program pwn_dispatch_probe.aleo {
    fn deposit(public token: identifier, input: dyn record, public amount: u128) -> (dyn record, Final) {
        let (change, deposit) = Arc20@(token)::transfer_private_to_public(input, std::ctx::addr(), amount);
        return (change, final {
            let balance = Stable@(token)::balances.get_or_use(std::ctx::addr(), 0u128);
            deposit.run();
            assert(Stable@(token)::balances.get_or_use(std::ctx::addr(), 0u128) == balance + amount);
            let stable = Stable@(token)::balances.get_or_use(std::ctx::addr(), 0u128);
            assert(stable >= amount);
        });
    }
    @noupgrade constructor() {}
}
