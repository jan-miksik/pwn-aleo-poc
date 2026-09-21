// Testnet demo: bootstrap admin is the deployer; a multisig replaces it via set_admin later.
const BOOTSTRAP: address = aleo1l53e5k624kfh0q78phyxzkvvxq54w89jk36emmzvjmxgkhh8cvyq8hp23s;
struct Settings { admin: address, upgrader: address, protocol_fee_bps: u16 }
program pwn_config_demo.aleo {
    mapping settings: bool => Settings;
    fn initialize() -> Final {
        assert_eq(std::ctx::signer(), BOOTSTRAP);
        return final {
            assert(!settings.contains(true));
            settings.set(true, Settings { admin: BOOTSTRAP, upgrader: BOOTSTRAP, protocol_fee_bps: 0u16 });
        };
    }
    fn set_admin(public admin: address, public upgrader: address) -> Final {
        let sender = std::ctx::signer();
        return final {
            assert_eq(settings.get(true).admin, sender);
            settings.set(true, Settings { admin: admin, upgrader: upgrader, protocol_fee_bps: 0u16 });
        };
    }
    // Upgrader is configuration only; this experiment is intentionally immutable.
    @noupgrade
    constructor() {}
}
