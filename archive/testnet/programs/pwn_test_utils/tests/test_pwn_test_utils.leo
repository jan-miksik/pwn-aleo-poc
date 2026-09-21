import pwn_test_utils.aleo;
program test_pwn_test_utils.aleo {
    @test
    fn domain_separation() {
        let lender = pwn_test_utils.aleo::auth(1u8, std::ctx::signer(), 111field);
        let borrower = pwn_test_utils.aleo::auth(2u8, std::ctx::signer(), 111field);
        assert_neq(lender, borrower);
    }
    @noupgrade
    constructor() {}
}
