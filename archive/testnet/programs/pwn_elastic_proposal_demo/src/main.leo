import credits.aleo;
import pwn_config_demo.aleo;
import pwn_hub_demo.aleo;

// Amounts are atomic units. Ratios have denominator 10,000 and round UP.
// credit_asset is fixed to credits.aleo; collateral_asset is a registry token ID.
export struct Terms {
    credit_asset: address,
    collateral_asset: field,
    min_draw: u64,
    max_draw: u64,
    collateral_ratio: u64,
    repayment_ratio: u64,
    duration: u32,
    expiry: u32,
    lender_auth: field,
}
struct Authority { domain: u8, account: address, salt: field }
struct ModuleTag { module: address, tag: u8 }
program pwn_elastic_proposal_demo.aleo {
    mapping terms_hash: field => field;
    mapping available_credit: field => u64;
    mapping repayments: field => u64;
    mapping closed: field => bool;

    fn open_commitment(public id: field, public terms: Terms,
        input: credits.aleo::credits, public amount: u64, salt: field)
        -> (credits.aleo::credits, Final) {
        assert_eq(terms.credit_asset, credits.aleo);
        assert_eq(terms.lender_auth, BHP256::hash_to_field(Authority { domain: 1u8, account: std::ctx::signer(), salt: salt }));
        assert(terms.min_draw > 0u64 && terms.max_draw >= terms.min_draw);
        assert(amount >= terms.min_draw);
        assert(terms.collateral_ratio > 0u64 && terms.repayment_ratio >= 10000u64);
        assert(terms.duration > 0u32);
        let hash = BHP256::hash_to_field(terms);
        let product = BHP256::hash_to_field(ModuleTag { module: std::ctx::addr(), tag: 2u8 });
        let (change, deposit) = credits.aleo::transfer_private_to_public(input, std::ctx::addr(), amount);
        return (change, final {
            assert(pwn_hub_demo.aleo::approved.get_or_use(product, false));
            assert_eq(pwn_config_demo.aleo::settings.get(true).protocol_fee_bps, 0u16);
            assert(!terms_hash.contains(id));
            assert(std::ctx::block_height() < terms.expiry);
            terms_hash.set(id, hash);
            available_credit.set(id, amount);
            repayments.set(id, 0u64);
            closed.set(id, false);
            deposit.run();
        });
    }

    // Only the immutable loan module may draw. Hub approval alone cannot
    // authorize arbitrary programs to drain the aggregate escrow.
    fn draw(public id: field, public terms: Terms, public amount: u64, recipient: address)
        -> (credits.aleo::credits, Final) {
        assert_eq(std::ctx::caller(), pwn_loan_demo.aleo);
        assert_eq(recipient, std::ctx::signer());
        assert(amount >= terms.min_draw && amount <= terms.max_draw);
        let hash = BHP256::hash_to_field(terms);
        let loan = BHP256::hash_to_field(ModuleTag { module: pwn_loan_demo.aleo, tag: 1u8 });
        let product = BHP256::hash_to_field(ModuleTag { module: std::ctx::addr(), tag: 2u8 });
        let (output, payout) = credits.aleo::transfer_public_to_private(recipient, amount);
        return (output, final {
            assert(pwn_hub_demo.aleo::approved.get_or_use(loan, false));
            assert(pwn_hub_demo.aleo::approved.get_or_use(product, false));
            assert_eq(terms_hash.get(id), hash);
            assert(!closed.get(id));
            assert(std::ctx::block_height() < terms.expiry);
            let remaining = available_credit.get(id) - amount;
            available_credit.set(id, remaining);
            payout.run();
        });
    }

    fn receive_repayment(public id: field, input: credits.aleo::credits, public amount: u64)
        -> (credits.aleo::credits, Final) {
        assert_eq(std::ctx::caller(), pwn_loan_demo.aleo);
        let (change, deposit) = credits.aleo::transfer_private_to_public(input, std::ctx::addr(), amount);
        return (change, final {
            let due = repayments.get(id);
            repayments.set(id, due + amount);
            deposit.run();
        });
    }

    fn cancel_commitment(public id: field, public terms: Terms, salt: field, public amount: u64)
        -> (credits.aleo::credits, Final) {
        assert_eq(terms.lender_auth, BHP256::hash_to_field(Authority { domain: 1u8, account: std::ctx::signer(), salt: salt }));
        let hash = BHP256::hash_to_field(terms);
        let (output, payout) = credits.aleo::transfer_public_to_private(std::ctx::signer(), amount);
        return (output, final {
            assert_eq(terms_hash.get(id), hash);
            assert(!closed.get(id));
            assert_eq(available_credit.get(id), amount);
            available_credit.set(id, 0u64);
            closed.set(id, true);
            payout.run();
        });
    }

    fn withdraw_repayment(public id: field, public terms: Terms, salt: field, public amount: u64)
        -> (credits.aleo::credits, Final) {
        assert(amount > 0u64);
        assert_eq(terms.lender_auth, BHP256::hash_to_field(Authority { domain: 1u8, account: std::ctx::signer(), salt: salt }));
        let hash = BHP256::hash_to_field(terms);
        let (output, payout) = credits.aleo::transfer_public_to_private(std::ctx::signer(), amount);
        return (output, final {
            assert_eq(terms_hash.get(id), hash);
            let remaining = repayments.get(id) - amount;
            repayments.set(id, remaining);
            payout.run();
        });
    }
    @noupgrade
    constructor() {}
}
