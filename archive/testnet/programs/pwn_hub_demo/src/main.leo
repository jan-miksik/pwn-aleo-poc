import pwn_config_demo.aleo;
struct ModuleTag { module: address, tag: u8 }
program pwn_hub_demo.aleo {
    // 1 = ACTIVE_LOAN, 2 = LOAN_PRODUCT.
    mapping approved: field => bool;
    fn set_tag(public module: address, public tag: u8, public enabled: bool) -> Final {
        assert(tag == 1u8 || tag == 2u8);
        let sender = std::ctx::signer();
        let key = BHP256::hash_to_field(ModuleTag { module: module, tag: tag });
        return final {
            assert_eq(pwn_config_demo.aleo::settings.get(true).admin, sender);
            approved.set(key, enabled);
        };
    }
    @noupgrade
    constructor() {}
}
