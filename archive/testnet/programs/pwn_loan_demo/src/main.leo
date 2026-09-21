import credits.aleo;
import token_registry.aleo;
import pwn_elastic_proposal_demo.aleo;

struct Authority { domain: u8, account: address, salt: field }
export struct Loan {
    loan_id: field,
    commitment_id: field,
    credit_amount: u64,
    collateral_asset: field,
    collateral_amount: u128,
    repayment_amount: u64,
    borrower_auth: field,
    lender_auth: field,
}
struct State { witness_hash: field, maturity: u32, status: u8 }
fn rounded(amount: u64, ratio: u64) -> u128 {
    return ((amount as u128) * (ratio as u128) + 9999u128) / 10000u128;
}
program pwn_loan_demo.aleo {
    // 1 active; 2 repaid; 3 defaulted. Keep tombstones to prevent ID replay.
    mapping loans: field => State;

    fn accept(public id: field, public commitment_id: field,
        public terms: pwn_elastic_proposal_demo.aleo::Terms, public credit_amount: u64,
        collateral: token_registry.aleo::Token, borrower_salt: field)
        -> (credits.aleo::credits, token_registry.aleo::Token, public Loan, Final) {
        assert_eq(collateral.token_id, terms.collateral_asset);
        // Authorization-gated assets require an external service to authorize
        // escrow and returned records. Explicitly unsupported in this build.
        assert(!collateral.external_authorization_required);
        let collateral_amount = rounded(credit_amount, terms.collateral_ratio);
        let repayment_amount = rounded(credit_amount, terms.repayment_ratio) as u64;
        let borrower_auth = BHP256::hash_to_field(Authority { domain: 2u8, account: std::ctx::signer(), salt: borrower_salt });
        let witness = Loan { loan_id: id, commitment_id: commitment_id,
            credit_amount: credit_amount, collateral_asset: terms.collateral_asset,
            collateral_amount: collateral_amount, repayment_amount: repayment_amount,
            borrower_auth: borrower_auth, lender_auth: terms.lender_auth };
        let hash = BHP256::hash_to_field(witness);
        let duration = terms.duration;
        let (change, lock) = token_registry.aleo::transfer_private_to_public(std::ctx::addr(), collateral_amount, collateral);
        let (credit, draw) = pwn_elastic_proposal_demo.aleo::draw(commitment_id, terms, credit_amount, std::ctx::signer());
        return (credit, change, witness, final {
            assert(!loans.contains(id));
            loans.set(id, State { witness_hash: hash, maturity: std::ctx::block_height() + duration, status: 1u8 });
            lock.run();
            draw.run();
        });
    }

    fn repay(public witness: Loan, input: credits.aleo::credits, borrower_salt: field)
        -> (credits.aleo::credits, token_registry.aleo::Token, Final) {
        assert_eq(witness.borrower_auth, BHP256::hash_to_field(Authority { domain: 2u8, account: std::ctx::signer(), salt: borrower_salt }));
        let hash = BHP256::hash_to_field(witness);
        let (change, pay) = pwn_elastic_proposal_demo.aleo::receive_repayment(witness.commitment_id, input, witness.repayment_amount);
        let (collateral, release) = token_registry.aleo::transfer_public_to_private(witness.collateral_asset, std::ctx::signer(), witness.collateral_amount, false);
        return (change, collateral, final {
            let state = loans.get(witness.loan_id);
            assert_eq(state.witness_hash, hash);
            assert_eq(state.status, 1u8);
            // No repay/default race at maturity: repay strictly before, claim at/after.
            assert(std::ctx::block_height() < state.maturity);
            loans.set(witness.loan_id, State { witness_hash: hash, maturity: state.maturity, status: 2u8 });
            pay.run();
            release.run();
        });
    }

    fn claim_default(public witness: Loan, lender_salt: field)
        -> (token_registry.aleo::Token, Final) {
        assert_eq(witness.lender_auth, BHP256::hash_to_field(Authority { domain: 1u8, account: std::ctx::signer(), salt: lender_salt }));
        let hash = BHP256::hash_to_field(witness);
        let (collateral, release) = token_registry.aleo::transfer_public_to_private(witness.collateral_asset, std::ctx::signer(), witness.collateral_amount, false);
        return (collateral, final {
            let state = loans.get(witness.loan_id);
            assert_eq(state.witness_hash, hash);
            assert_eq(state.status, 1u8);
            assert(std::ctx::block_height() >= state.maturity);
            loans.set(witness.loan_id, State { witness_hash: hash, maturity: state.maturity, status: 3u8 });
            release.run();
        });
    }
    @noupgrade
    constructor() {}
}
