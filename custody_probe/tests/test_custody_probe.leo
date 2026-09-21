import custody_probe.aleo;
import token_registry.aleo;
program test_custody_probe.aleo {
    @test
    fn round_trip() -> Final {
        let register = token_registry.aleo::register_token(987654321field, 1u128, 1u128, 6u8, 1000000u128, false, std::ctx::signer());
        let (input, mint) = token_registry.aleo::mint_private(987654321field, std::ctx::signer(), 1000u128, false, 4294967295u32);
        let (change, deposit) = custody_probe.aleo::deposit(input, 600u128);
        let (output, withdraw) = custody_probe.aleo::withdraw(987654321field, std::ctx::signer(), 600u128);
        assert_eq(change.amount, 400u128);
        assert_eq(output.amount, 600u128);
        assert_eq(output.owner, std::ctx::signer());
        return final { register.run(); mint.run(); deposit.run(); withdraw.run(); };
    }
    @noupgrade
    constructor() {}
}
