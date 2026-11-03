"""Canonical renderers for commitment offers and borrower collateral reservations.

Kept separate from token entry-point plumbing. All programs are still generated
by generate_multitoken.py; these helpers introduce no additional custody program.
"""


def offer_types():
    return '''export struct OfferTerms {
    direction: u8, credit_asset: Asset, collateral_asset: Asset,
    min_draw: u128, max_draw: u128, collateral_ratio: u64, repayment_ratio: u64,
    accruing_apr: u32, duration: u32, expiry: u32, maker_auth: field,
}
export struct OfferOpening { recipient: address, taker: address, salt: field }
export struct OfferWitness { terms: OfferTerms, opening: OfferOpening, private_offer: bool }
export struct BorrowFunding { requested: u128, collateral: u128 }
export struct OfferCommitment {
    protocol: address, module: identifier, terms: OfferTerms,
    opening: OfferOpening, private_offer: bool,
}
export struct BorrowFillId {
    protocol: address, module: identifier, offer_id: field,
    borrower_auth: field, lender_auth: field, nonce: field,
}
'''


def offer_helpers(hub, core):
    return f'''
fn validate_offer_terms(terms: {hub}::OfferTerms) {{
    assert(terms.direction == 1u8 || terms.direction == 2u8);
    validate_asset(terms.credit_asset);
    validate_asset(terms.collateral_asset);
    assert(terms.min_draw > 0u128 && terms.max_draw >= terms.min_draw);
    assert(terms.collateral_ratio > 0u64 && terms.collateral_ratio <= 1000000u64);
    assert(terms.repayment_ratio >= 10000u64 && terms.repayment_ratio <= 1000000u64);
    assert(terms.accruing_apr <= 100000u32);
    assert(terms.duration >= 10u32 && terms.duration <= 3153600u32);
    let collateral = rounded(terms.max_draw, terms.collateral_ratio);
    let repayment = rounded(terms.max_draw, terms.repayment_ratio);
    assert(collateral > 0u128 && repayment > 0u128);
    if terms.collateral_asset.family == 1u8 {{ assert(collateral <= 18446744073709551615u128); }}
    if terms.credit_asset.family == 1u8 {{
        assert(terms.max_draw <= 18446744073709551615u128);
        assert(repayment + accrued(terms.max_draw, terms.accruing_apr, terms.duration * 10u32) <= 18446744073709551615u128);
    }}
}}
fn offer_commitment(module: identifier, terms: {hub}::OfferTerms,
    opening: {hub}::OfferOpening, private_offer: bool) -> field {{
    assert(opening.salt != 0field);
    return BHP256::hash_to_field({hub}::OfferCommitment {{
        protocol: {core}, module: module, terms: terms,
        opening: opening, private_offer: private_offer
    }});
}}
fn check_offer_fill(terms: {hub}::OfferTerms, principal: u128,
    collateral: u128, repayment: u128, apr: u32, duration: u32) {{
    assert(principal >= terms.min_draw && principal <= terms.max_draw);
    assert_eq(collateral, rounded(principal, terms.collateral_ratio));
    assert_eq(repayment, rounded(principal, terms.repayment_ratio));
    assert_eq(apr, terms.accruing_apr);
    assert_eq(duration, terms.duration);
}}
fn empty_offer_terms() -> {hub}::OfferTerms {{
    let asset = {hub}::Asset {{ program_id: 'credits', token_id: 0field, family: 1u8, version: 1u16 }};
    return {hub}::OfferTerms {{ direction: 0u8, credit_asset: asset, collateral_asset: asset,
        min_draw: 0u128, max_draw: 0u128, collateral_ratio: 0u64, repayment_ratio: 0u64,
        accruing_apr: 0u32, duration: 0u32, expiry: 0u32, maker_auth: 0field }};
}}
final fn require_reserve(asset: {hub}::Asset, total: u128) {{
    if asset.family == 1u8 {{ assert(credits.aleo::account.get_or_use(std::ctx::addr(), 0u64) as u128 >= total); }}
    else {{ assert(Reserves@(asset.program_id)::balances.get_or_use(std::ctx::addr(), 0u128) >= total); }}
}}
'''


def lender_extensions(g, module):
    hub, core, config = (g[n] for n in ('H', 'L', 'C'))
    rec, proof, sig, outputs, family, deposit, payout, before, after, balance = (
        g[n] for n in ('rec', 'proof', 'sig', 'outputs', 'family', 'deposit', 'payout', 'before', 'after', 'balance'))
    s = '''
    mapping private_expiry: field => u32;
    mapping loan_repayments: field => u128;
    mapping repayment_hashes: field => field;
'''
    for k in g['FAMILIES']:
        s += f'''
    fn open_private_{k}(public nonce: field, terms: {hub}::OfferTerms, opening: {hub}::OfferOpening,
        input: {rec(k)}, public amount: u128, maker_salt: field{proof(k)})
        -> {sig([k], [rec(k), 'public field', 'Final'])} {{
        validate_offer_terms(terms); assert_eq(terms.direction, 1u8);
        assert_eq(terms.maker_auth, authority_hash::[1u8, {core}](maker_salt));
        assert_eq(opening.recipient, std::ctx::signer());
        assert(amount >= terms.min_draw);
        let asset = terms.credit_asset; {family(k, 'asset')}
        let expiry = terms.expiry;
        let id = position_id::[3u8, {module}](terms.maker_auth, nonce);
        let hash = offer_commitment('{module[:-5]}', terms, opening, true);
        {deposit(k, 'asset', 'amount', 'input')}
        return ({outputs([(k, 'compliance')], ['change', 'id'])}, final {{
            assert({hub}::offer_modules.get_or_use('{module[:-5]}', false));
            assert_eq({config}::settings.get(true).protocol_fee_bps, 0u16);
            assert(!terms_hash.contains(id));
            assert(std::ctx::block_height() < expiry);
            let total = liabilities.get_or_use(asset.program_id, 0u128); {before(k, 'asset')}
            terms_hash.set(id, hash); private_expiry.set(id, expiry);
            credit_assets.set(id, asset); available_credit.set(id, amount);
            repayments.set(id, 0u128); closed.set(id, false);
            liabilities.set(asset.program_id, total + amount);
            deposit.run(); {after(k, 'asset', 'amount', '+')}
        }});
    }}
'''
        for op in ('cancel', 'withdraw'):
            action = 'cancel_available(id, amount);' if op == 'cancel' else 'repayments.set(id, repayments.get(id) - amount);'
            s += f'''
    fn {op}_private_{k}(public id: field, terms: {hub}::OfferTerms,
        opening: {hub}::OfferOpening, maker_salt: field, public amount: u128)
        -> {sig([k], [rec(k), 'Final'])} {{
        assert_eq(terms.direction, 1u8);
        assert_eq(terms.maker_auth, authority_hash::[1u8, {core}](maker_salt));
        {'assert(amount > 0u128);' if op == 'withdraw' else ''}
        let asset = terms.credit_asset; {family(k, 'asset')}
        let hash = offer_commitment('{module[:-5]}', terms, opening, true);
        {payout(k, 'asset', 'amount', 'std::ctx::signer()')}
        return ({outputs([(k, 'compliance')], ['output'])}, final {{
            assert_eq(terms_hash.get(id), hash);
            let total = liabilities.get(asset.program_id); {before(k, 'asset')}
            {action} liabilities.set(asset.program_id, total - amount);
            payout.run(); {after(k, 'asset', 'amount', '-')}
        }});
    }}
'''
        s += f'''
    fn withdraw_loan_{k}(public witness: {core}::Loan, lender_salt: field, public amount: u128)
        -> {sig([k], [rec(k), 'Final'])} {{
        assert(witness.borrower_offer); assert(amount > 0u128);
        assert_eq(witness.lender_auth, authority_hash::[1u8, {core}](lender_salt));
        {family(k, 'witness.credit_asset')}
        let hash = BHP256::hash_to_field(witness);
        {payout(k, 'witness.credit_asset', 'amount', 'std::ctx::signer()')}
        return ({outputs([(k, 'compliance')], ['output'])}, final {{
            assert_eq(repayment_hashes.get(witness.loan_id), hash);
            let total = liabilities.get(witness.credit_asset.program_id); {before(k, 'witness.credit_asset')}
            loan_repayments.set(witness.loan_id, loan_repayments.get(witness.loan_id) - amount);
            liabilities.set(witness.credit_asset.program_id, total - amount);
            payout.run(); {after(k, 'witness.credit_asset', 'amount', '-')}
        }});
    }}
'''
    return s



def borrower_extensions(g):
    hub, core, config = (g[n] for n in ('H', 'L', 'C'))
    rec, proof, sig, outputs, family, deposit, payout, before, after, balance = (
        g[n] for n in ('rec', 'proof', 'sig', 'outputs', 'family', 'deposit', 'payout', 'before', 'after', 'balance'))
    s = f'''
    // Total liabilities include unused borrower reservations and active loan collateral.
    mapping borrow_hashes: field => field;
    mapping borrow_public_terms: field => {hub}::OfferTerms;
    mapping borrow_remaining: field => u128;
    mapping borrow_collateral: field => u128;
    mapping borrow_expiry: field => u32;
    mapping borrow_closed: field => bool;
'''
    for k in g['FAMILIES']:
        s += f'''
    // Private offers require a canonical empty public listing; no secret terms enter finalize.
    fn open_borrow_{k}(public nonce: field, public offer_module: identifier,
        public listing: {hub}::OfferTerms, offer: {hub}::OfferWitness,
        input: {rec(k)}, public funding: {hub}::BorrowFunding, borrower_salt: field{proof(k)})
        -> {sig([k], [rec(k), 'public field', 'Final'])} {{
        let terms = offer.terms; let opening = offer.opening;
        validate_offer_terms(terms); assert_eq(terms.direction, 2u8);
        assert_eq(terms.maker_auth, authority_hash::[2u8, {core}](borrower_salt));
        assert_eq(opening.recipient, std::ctx::signer());
        if offer.private_offer {{ assert_eq(listing, empty_offer_terms()); }}
        else {{ assert_eq(listing, terms); }}
        assert(funding.requested >= terms.min_draw);
        assert(funding.collateral >= rounded(funding.requested, terms.collateral_ratio));
        let asset = terms.collateral_asset; {family(k, 'asset')}
        let expiry = terms.expiry; let private_offer = offer.private_offer;
        let id = position_id::[4u8, {core}](terms.maker_auth, nonce);
        let hash = offer_commitment(offer_module, terms, opening, private_offer);
        let core_tag = BHP256::hash_to_field(ModuleTag {{ module: {core}, tag: 1u8 }});
        {deposit(k, 'asset', 'funding.collateral', 'input')}
        return ({outputs([(k, 'compliance')], ['change', 'id'])}, final {{
            assert({hub}::offer_modules.get_or_use(offer_module, false));
            assert({hub}::approved.get_or_use(core_tag, false));
            assert_eq({config}::settings.get(true).protocol_fee_bps, 0u16);
            assert(!borrow_hashes.contains(id)); assert(std::ctx::block_height() < expiry);
            let total = liabilities.get_or_use(asset.program_id, 0u128); {before(k, 'asset')}
            borrow_hashes.set(id, hash); borrow_expiry.set(id, expiry);
            borrow_remaining.set(id, funding.requested); borrow_collateral.set(id, funding.collateral);
            borrow_closed.set(id, false);
            if !private_offer {{ borrow_public_terms.set(id, listing); }}
            liabilities.set(asset.program_id, total + funding.collateral);
            deposit.run(); {after(k, 'asset', 'funding.collateral', '+')}
        }});
    }}
    fn cancel_borrow_{k}(public id: field, public offer_module: identifier,
        offer: {hub}::OfferWitness, borrower_salt: field, public amount: u128)
        -> {sig([k], [rec(k), 'Final'])} {{
        assert_eq(offer.terms.direction, 2u8);
        assert_eq(offer.terms.maker_auth, authority_hash::[2u8, {core}](borrower_salt));
        let asset = offer.terms.collateral_asset; {family(k, 'asset')}
        let hash = offer_commitment(offer_module, offer.terms, offer.opening, offer.private_offer);
        {payout(k, 'asset', 'amount', 'std::ctx::signer()')}
        return ({outputs([(k, 'compliance')], ['output'])}, final {{
            assert_eq(borrow_hashes.get(id), hash); assert(!borrow_closed.get(id));
            assert_eq(borrow_collateral.get(id), amount);
            let total = liabilities.get(asset.program_id); {before(k, 'asset')}
            borrow_closed.set(id, true); borrow_remaining.set(id, 0u128); borrow_collateral.set(id, 0u128);
            liabilities.set(asset.program_id, total - amount);
            payout.run(); {after(k, 'asset', 'amount', '-')}
        }});
    }}
'''
    for c in g['FAMILIES']:
        s += f'''
    fn accept_borrow_{c}(public nonce: field, public offer_module: identifier, public commitment_id: field,
        offer: {hub}::OfferWitness, input: {rec(c)}, public amount: u128, lender_salt: field{proof(c)})
        -> {sig([c, c], [rec(c), 'dyn record', 'public Loan', 'Final'])} {{
        let terms = offer.terms; let opening = offer.opening;
        assert_eq(terms.direction, 2u8);
        assert(amount >= terms.min_draw && amount <= terms.max_draw);
        assert(!offer.private_offer || opening.taker == std::ctx::signer());
        {family(c, 'terms.credit_asset')} validate_asset(terms.collateral_asset);
        let offer_hash = offer_commitment(offer_module, terms, opening, offer.private_offer);
        let lender_auth = authority_hash::[1u8, {core}](lender_salt);
        let id = BHP256::hash_to_field({hub}::BorrowFillId {{
            protocol: {core}, module: offer_module, offer_id: commitment_id,
            borrower_auth: terms.maker_auth, lender_auth: lender_auth, nonce: nonce
        }});
        let witness = Loan {{
            loan_id: id, offer_module: offer_module, commitment_id: commitment_id,
            credit_asset: terms.credit_asset, collateral_asset: terms.collateral_asset,
            credit_amount: amount, collateral_amount: rounded(amount, terms.collateral_ratio),
            repayment_amount: rounded(amount, terms.repayment_ratio), accruing_apr: terms.accruing_apr,
            borrower_auth: terms.maker_auth, lender_auth: lender_auth, borrower_offer: true
        }};
        let hash = BHP256::hash_to_field(witness); let duration = terms.duration;
        let core_tag = BHP256::hash_to_field(ModuleTag {{ module: {core}, tag: 1u8 }});
        {deposit(c, 'witness.credit_asset', 'amount', 'input', 'funding')}
        {payout(c, 'witness.credit_asset', 'amount', 'opening.recipient', 'delivery', 'credit', 'credit_compliance')}
        return ({outputs([(c, 'compliance'), (c, 'credit_compliance')], ['change', 'credit as dyn record' if c == 'aleo' else 'credit', 'witness'])}, final {{
            assert({hub}::offer_modules.get_or_use(offer_module, false));
            assert({hub}::approved.get_or_use(core_tag, false));
            assert_eq(borrow_hashes.get(commitment_id), offer_hash);
            assert(!borrow_closed.get(commitment_id));
            assert(std::ctx::block_height() < borrow_expiry.get(commitment_id));
            assert(!loans.contains(id));
            let reserved = liabilities.get(witness.collateral_asset.program_id);
            require_reserve(witness.collateral_asset, reserved);
            let credit_total = liabilities.get_or_use(witness.credit_asset.program_id, 0u128);
            let credit_before = {balance(c, 'witness.credit_asset')}; assert(credit_before >= credit_total);
            borrow_remaining.set(commitment_id, borrow_remaining.get(commitment_id) - amount);
            borrow_collateral.set(commitment_id, borrow_collateral.get(commitment_id) - witness.collateral_amount);
            // Reclassify reserved collateral as active; total token liabilities do not change.
            loans.set(id, State {{ witness_hash: hash, maturity: std::ctx::block_height() + duration,
                start: std::ctx::block_height() as i64, status: 1u8 }});
            funding.run();
            assert_eq({balance(c, 'witness.credit_asset')}, credit_before + amount);
            delivery.run();
            assert_eq({balance(c, 'witness.credit_asset')}, credit_before);
        }});
    }}
'''
    return s
