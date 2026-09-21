// Quotient/remainder avoids overflowing amount*ratio when the result fits u128.
fn rounded(amount: u128, ratio: u64) -> u128 {
    return (amount / 10000u128) * (ratio as u128)
        + ((amount % 10000u128) * (ratio as u128) + 9999u128) / 10000u128;
}
fn accrued(principal: u128, apr: u32, elapsed: u32) -> u128 {
    let rate_time = (apr as u128) * (elapsed as u128);
    return (principal / 315360000000u128) * rate_time
        + ((principal % 315360000000u128) * rate_time) / 315360000000u128;
}

program pwn_math_fuzz.aleo {
    fn check_rounded(amount: u128, ratio: u64) -> u128 { return rounded(amount, ratio); }
    fn check_accrued(amount: u128, apr: u32, elapsed: u32) -> u128 { return accrued(amount, apr, elapsed); }
    fn check_native(amount: u128) -> u64 { return amount as u64; }
    @noupgrade constructor() {}
}
