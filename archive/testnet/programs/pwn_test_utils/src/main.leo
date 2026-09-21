// Offline fixture calculation only; never deployed. No token or ledger mocks.
struct Authority { domain: u8, account: address, salt: field }
program pwn_test_utils.aleo {
    fn auth(domain: u8, account: address, salt: field) -> field {
        return BHP256::hash_to_field(Authority { domain: domain, account: account, salt: salt });
    }
    @noupgrade
    constructor() {}
}
