
program pwn_delta_token.aleo {
    record Token { owner: address, amount: u128 }
    mapping balances: address => u128;
    mapping bad: bool => bool;
    fn set_bad(public value: bool) -> Final { return final { bad.set(true, value); }; }
    fn mint(recipient: address, amount: u128) -> Token { return Token { owner: recipient, amount: amount }; }
    fn transfer_private_to_public(input: Token, public recipient: address, public amount: u128) -> (Token, Final) {
        let change = Token { owner: input.owner, amount: input.amount - amount };
        return (change, final {
            let received = bad.get_or_use(true, false) ? amount - 1u128 : amount;
            balances.set(recipient, balances.get_or_use(recipient, 0u128) + received);
        });
    }
    fn transfer_public_to_private(recipient: address, public amount: u128) -> (Token, Final) {
        let output = Token { owner: recipient, amount: amount }; let caller = std::ctx::caller();
        return (output, final { balances.set(caller, balances.get(caller) - amount); });
    }
    @noupgrade constructor() {}
}
