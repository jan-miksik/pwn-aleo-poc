"""Shared Leo business logic rendered into the existing custody programs.

These are internal helpers, not separately deployed programs. Proof helpers
may compile to local closures; final helpers inline in Leo 4.4.2. Token calls
and reserve checks stay in the entry-point templates so their ordering remains visible.
"""


def shared_logic(hub):
    return f'''
// Internal proof helpers: keep authorization domains and asset profiles explicit.
fn authority_hash::[DOMAIN: u8, PROTOCOL: address](salt: field) -> field {{
    return BHP256::hash_to_field(Authority {{ domain: DOMAIN, protocol: PROTOCOL, account: std::ctx::signer(), salt: salt }});
}}
fn position_id::[DOMAIN: u8, PROTOCOL: address](authority: field, nonce: field) -> field {{
    return BHP256::hash_to_field(PositionId {{ domain: DOMAIN, protocol: PROTOCOL, authority: authority, nonce: nonce }});
}}
fn validate_aleo_asset::[VERSION: u16](asset: {hub}::Asset) {{
    assert_eq(asset.family, 1u8);
    assert_eq(asset.version, VERSION);
    assert_eq(asset.token_id, 0field);
    assert_eq(asset.program_id, 'credits');
}}
fn validate_token_asset::[FAMILY: u8](asset: {hub}::Asset) {{
    assert_eq(asset.family, FAMILY);
    assert_eq(asset.version, 1u16);
    assert_eq(asset.token_id, 0field);
    assert(asset.program_id != 'credits');
}}
'''


def proposal_logic(config, hub, proposal):
    return f'''
// Admission applies only to new exposure; settlement must survive delisting.
const MIN_DURATION_BLOCKS: u32 = 10u32;
const MAX_DURATION_BLOCKS: u32 = 3153600u32;
const MAX_APR_BPS: u32 = 100000u32;
const MAX_RATIO_BPS: u64 = 1000000u64;
const SECONDS_PER_BLOCK: u32 = 10u32;
final fn require_enabled(asset: {hub}::Asset) {{
    let policy = {hub}::assets.get(asset.program_id);
    assert(policy.enabled);
    assert_eq(policy.family, asset.family);
    assert_eq(policy.version, asset.version);
    assert_eq(asset.token_id, 0field);
}}
fn validate_open_terms(terms: Terms, amount: u128, salt: field) {{
    assert_eq(terms.lender_auth, authority_hash::[1u8, {proposal}](salt));
    assert(terms.min_draw > 0u128 && terms.max_draw >= terms.min_draw && amount >= terms.min_draw);
    assert(terms.collateral_ratio > 0u64 && terms.collateral_ratio <= MAX_RATIO_BPS);
    assert(terms.repayment_ratio >= 10000u64 && terms.repayment_ratio <= MAX_RATIO_BPS);
    assert(terms.accruing_apr <= MAX_APR_BPS);
    assert(terms.duration >= MIN_DURATION_BLOCKS && terms.duration <= MAX_DURATION_BLOCKS);
    let max_collateral = rounded(terms.max_draw, terms.collateral_ratio);
    let max_repayment = rounded(terms.max_draw, terms.repayment_ratio);
    assert(max_collateral > 0u128 && max_repayment > 0u128);
    if terms.collateral_asset.family == 1u8 {{ assert(max_collateral <= 18446744073709551615u128); }}
    if terms.credit_asset.family == 1u8 {{
        let scheduled_interest = accrued(terms.max_draw, terms.accruing_apr, terms.duration * SECONDS_PER_BLOCK);
        assert(terms.max_draw <= 18446744073709551615u128);
        assert(max_repayment + scheduled_interest <= 18446744073709551615u128);
    }}
}}
final fn validate_open(product: field, terms: Terms, id: field) {{
    assert({hub}::approved.get_or_use(product, false));
    assert_eq({config}::settings.get(true).protocol_fee_bps, 0u16);
    require_enabled(terms.credit_asset);
    require_enabled(terms.collateral_asset);
    assert(!terms_hash.contains(id));
    assert(std::ctx::block_height() < terms.expiry);
}}
final fn register_commitment(id: field, hash: field, asset: {hub}::Asset, amount: u128, total: u128) {{
    terms_hash.set(id, hash);
    credit_assets.set(id, asset);
    available_credit.set(id, amount);
    repayments.set(id, 0u128);
    closed.set(id, false);
    liabilities.set(asset.program_id, total + amount);
}}
final fn validate_draw(loan: field, product: field, terms: Terms, id: field, hash: field) {{
    assert({hub}::approved.get_or_use(loan, false) && {hub}::approved.get_or_use(product, false));
    require_enabled(terms.credit_asset);
    require_enabled(terms.collateral_asset);
    assert_eq(terms_hash.get(id), hash);
    assert_eq(credit_assets.get(id), terms.credit_asset);
    assert(!closed.get(id));
    assert(std::ctx::block_height() < terms.expiry);
}}
final fn debit_draw(id: field, token: identifier, amount: u128, total: u128) {{
    available_credit.set(id, available_credit.get(id) - amount);
    liabilities.set(token, total - amount);
}}
final fn credit_repayment(id: field, token: identifier, amount: u128, total: u128) {{
    repayments.set(id, repayments.get(id) + amount);
    liabilities.set(token, total + amount);
}}
final fn cancel_available(id: field, amount: u128) {{
    assert(!closed.get(id));
    assert_eq(available_credit.get(id), amount);
    available_credit.set(id, 0u128);
    closed.set(id, true);
}}
'''


def loan_logic(proposal):
    return f'''
// Interest accrues per finalized block at the nominal block time; the proposal uses the same constant for the native u64 bound.
const SECONDS_PER_BLOCK: u32 = 10u32;
fn make_loan::[PROTOCOL: address](
    nonce: field, commitment_id: field, terms: {proposal}::Terms,
    credit_amount: u128, collateral_amount: u128, repayment_amount: u128, borrower_salt: field
) -> (field, Loan) {{
    let borrower_auth = authority_hash::[2u8, PROTOCOL](borrower_salt);
    let id = position_id::[2u8, PROTOCOL](borrower_auth, nonce);
    let witness = Loan {{ loan_id: id, commitment_id: commitment_id,
        credit_asset: terms.credit_asset, collateral_asset: terms.collateral_asset,
        credit_amount: credit_amount, collateral_amount: collateral_amount, repayment_amount: repayment_amount,
        accruing_apr: terms.accruing_apr, borrower_auth: borrower_auth, lender_auth: terms.lender_auth }};
    return (id, witness);
}}
fn repayment_witness_hash::[PROTOCOL: address](witness: Loan, amount: u128, borrower_salt: field) -> field {{
    assert(amount >= witness.repayment_amount);
    assert_eq(witness.borrower_auth, authority_hash::[2u8, PROTOCOL](borrower_salt));
    return BHP256::hash_to_field(witness);
}}
final fn register_loan(id: field, witness: Loan, hash: field, terms: {proposal}::Terms, collateral_amount: u128, total: u128) {{
    loans.set(id, State {{ witness_hash: hash, maturity: std::ctx::block_height() + terms.duration, start: std::ctx::block_height() as i64, status: 1u8 }});
    liabilities.set(witness.collateral_asset.program_id, total + collateral_amount);
}}
final fn validate_repayment(witness: Loan, hash: field, amount: u128) -> State {{
    let state = loans.get(witness.loan_id);
    assert_eq(state.witness_hash, hash);
    assert_eq(state.status, 1u8);
    let start = state.start as u32;
    assert(std::ctx::block_height() >= start);
    let elapsed = (std::ctx::block_height() - start) * SECONDS_PER_BLOCK;
    assert(amount >= witness.repayment_amount + accrued(witness.credit_amount, witness.accruing_apr, elapsed));
    return state;
}}
final fn validate_default(witness: Loan, hash: field) -> State {{
    let state = loans.get(witness.loan_id);
    assert_eq(state.witness_hash, hash);
    assert_eq(state.status, 1u8);
    assert(std::ctx::block_height() >= state.maturity);
    return state;
}}
// Separate call sites choose terminal status; token finalizers remain outside.
final fn settle_loan::[STATUS: u8](witness: Loan, hash: field, state: State, total: u128) {{
    loans.set(witness.loan_id, State {{ witness_hash: hash, maturity: state.maturity, start: state.start, status: STATUS }});
    liabilities.set(witness.collateral_asset.program_id, total - witness.collateral_amount);
}}
'''
