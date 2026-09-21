import merkle_tree.aleo;
import arc20_multisig_core.aleo;
import arc20_sol.aleo;
import arc20_wbtc.aleo;
import usdcx_multisig_core.aleo;
import usdcx_freezelist.aleo;
import usdcx_stablecoin.aleo;
import usad_multisig_core.aleo;
import usad_freezelist.aleo;
import usad_stablecoin.aleo;
import pwn_delta_token.aleo;
import credits.aleo;
import pwn_config_poc.aleo;
import pwn_hub_poc.aleo;
import pwn_proposal_poc.aleo;
import pwn_loan_poc.aleo;// Quotient/remainder avoids overflowing amount*ratio when the result fits u128.
fn rounded(amount: u128, ratio: u64) -> u128 {
    return (amount / 10000u128) * (ratio as u128)
        + ((amount % 10000u128) * (ratio as u128) + 9999u128) / 10000u128;
}
fn accrued(principal: u128, apr: u32, elapsed: u32) -> u128 {
    let rate_time = (apr as u128) * (elapsed as u128);
    return (principal / 315360000000u128) * rate_time
        + ((principal % 315360000000u128) * rate_time) / 315360000000u128;
}

struct Authority { domain: u8, protocol: address, account: address, salt: field }
program pwn_local_fixture.aleo {
    fn auth(account: address, salt: field) -> field {
        return BHP256::hash_to_field(Authority { domain: 1u8, protocol: pwn_proposal_poc.aleo, account: account, salt: salt });
    }
    fn freeze_root(account: address) -> field { return Poseidon4::hash_to_field([1field, 0field, account as field]); }
    fn math_round(amount: u128, ratio: u64) -> u128 { return rounded(amount, ratio); }
    fn math_interest(amount: u128, apr: u32, elapsed: u32) -> u128 { return accrued(amount, apr, elapsed); }
    fn dynamic_sol(input: arc20_sol.aleo::Token) -> dyn record { return input as dyn record; }
    fn forward_set_asset(public token: identifier, public family: u8, public enabled: bool) -> Final {
        let action = pwn_hub_poc.aleo::set_asset(token, family, enabled);
        return final { action.run(); };
    }
    fn forward_set_admin(public admin: address, public upgrader: address) -> Final {
        let action = pwn_config_poc.aleo::set_admin(admin, upgrader);
        return final { action.run(); };
    }
    @noupgrade constructor() {}
}
