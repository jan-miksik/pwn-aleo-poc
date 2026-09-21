#!/usr/bin/env python3
"""Generate the token-family lending programs (native ALEO, ARC-20, deployed compliance ABI). No keys, RPC, or deployment.

Custody remains in proposal/loan; interfaces are inlined, not custody adapters.
V2 schemas are deliberately untouched. New layouts require new program IDs.
"""
import json
from pathlib import Path
from multitoken_logic import shared_logic, proposal_logic, loan_logic
ROOT=Path(__file__).resolve().parents[1]
BOOT='aleo1l53e5k624kfh0q78phyxzkvvxq54w89jk36emmzvjmxgkhh8cvyq8hp23s'  # bootstrap/admin of the local devnode fixtures (published development key)
C='pwn_config_poc.aleo'; H='pwn_hub_poc.aleo'; P='pwn_proposal_poc.aleo'; L='pwn_loan_poc.aleo'
FAMILIES={'aleo':1,'arc20':2,'compliant':3}
AUTH='''struct Authority { domain: u8, protocol: address, account: address, salt: field }
struct PositionId { domain: u8, protocol: address, authority: field, nonce: field }
struct ModuleTag { module: address, tag: u8 }
struct UpgradeKey { module: address, edition: u16 }
'''
INTERFACES='''// Minimal transfer ABI; reserve profile v1 additionally requires balances[address]: u128.
interface Arc20 {
    record Token { owner: address, amount: u128, .. }
    fn transfer_private_to_public(input: Token, public recipient: address, public amount: u128) -> (Token, Final);
    fn transfer_public_to_private(recipient: address, public amount: u128) -> (Token, Final);
}
// Deployed USDCx/USAD ABI, not a claim of compatibility with every ARC-22 edition.
interface Compliant {
    record Token { owner: address, amount: u128, .. }
    record ComplianceRecord;
    fn transfer_private_to_public(public recipient: address, public amount: u128, input: Token, proofs: [pwn_hub_poc.aleo::MerkleProof; 2]) -> (ComplianceRecord, Token, Final);
    fn transfer_public_to_private(recipient: address, public amount: u128) -> (ComplianceRecord, Token, Final);
}
interface Reserves { mapping balances: address => u128; }
'''
MATH='''// Quotient/remainder avoids overflowing amount*ratio when the result fits u128.
fn rounded(amount: u128, ratio: u64) -> u128 {
    return (amount / 10000u128) * (ratio as u128)
        + ((amount % 10000u128) * (ratio as u128) + 9999u128) / 10000u128;
}
fn accrued(principal: u128, apr: u32, elapsed: u32) -> u128 {
    let rate_time = (apr as u128) * (elapsed as u128);
    return (principal / 315360000000u128) * rate_time
        + ((principal % 315360000000u128) * rate_time) / 315360000000u128;
}
'''
def upgrade(config=False):
    setting='settings' if config else C+'::settings'
    schedule='upgrade_after' if config else C+'::upgrade_after'
    return f'''    @custom
    constructor() {{
        if std::ctx::edition() == 0u16 {{ assert_eq(std::ctx::program_owner(), {BOOT}); }}
        else {{
            assert_eq(std::ctx::program_owner(), {setting}.get(true).upgrader);
            let key = BHP256::hash_to_field(UpgradeKey {{ module: std::ctx::addr(), edition: std::ctx::edition() }});
            assert(std::ctx::block_height() >= {schedule}.get(key));
        }}
    }}
'''
def auth(domain,program,salt): return f'authority_hash::[{domain}u8, {program}]({salt})'
def pos(domain,program,a):return f'position_id::[{domain}u8, {program}]({a}, nonce)'
def rec(k):return 'credits.aleo::credits' if k=='aleo' else 'dyn record'
def proof(k):return ', proofs: [pwn_hub_poc.aleo::MerkleProof; 2]' if k=='compliant' else ''
def sig(kinds,rest):return '('+', '.join(['dyn record' for k in kinds if k=='compliant']+rest)+')'
def outputs(kinds,rest):return ', '.join([label for k,label in kinds if k=='compliant']+rest)
def family(k,a):return f'validate_aleo_asset::[1u16]({a});' if k=='aleo' else f'validate_token_asset::[{FAMILIES[k]}u8]({a});'
def balance(k,a):return 'credits.aleo::account.get_or_use(std::ctx::addr(), 0u64) as u128' if k=='aleo' else f'Reserves@({a}.program_id)::balances.get_or_use(std::ctx::addr(), 0u128)'
def deposit(k,a,amount,record,label='deposit'):
    if k=='aleo':return f'let (change, {label}) = credits.aleo::transfer_private_to_public({record}, std::ctx::addr(), {amount} as u64);'
    if k=='arc20':return f'let (change, {label}) = Arc20@({a}.program_id)::transfer_private_to_public({record}, std::ctx::addr(), {amount});'
    return f'let (compliance, change, {label}) = Compliant@({a}.program_id)::transfer_private_to_public(std::ctx::addr(), {amount}, {record}, proofs);'
def payout(k,a,amount,recipient,label='payout',record='output',compliance='compliance'):
    if k=='aleo':return f'let ({record}, {label}) = credits.aleo::transfer_public_to_private({recipient}, {amount} as u64);'
    if k=='arc20':return f'let ({record}, {label}) = Arc20@({a}.program_id)::transfer_public_to_private({recipient}, {amount});'
    return f'let ({compliance}, {record}, {label}) = Compliant@({a}.program_id)::transfer_public_to_private({recipient}, {amount});'
def before(k,a):return f'let before = {balance(k,a)}; assert(before >= total);'
def after(k,a,amount,sign):return f'''// Postcondition checks the actual reserve delta, after the atomic token finalizer.
            assert_eq({balance(k,a)}, before {sign} {amount});'''

def render_programs():
    """Render canonical source/manifests without modifying the working tree."""
    files = {}

    def write(name, body, deps):
        directory = name[:-5]
        files[f'{directory}/src/main.leo'] = '// Generated by scripts/generate_multitoken.py.\n' + body
        files[f'{directory}/program.json'] = json.dumps(dict(program=name,version='0.3.0',description='Versioned multi-token lending',license='MIT',leo='4.4.2',dependencies=[dict(name=n,location='local',path='../vendor/credits.network.aleo' if n=='credits.aleo' else '../'+n[:-5],edition=None) for n in deps]),indent=2)+'\n'
        files[f'{directory}/.gitignore'] = 'build/\noutputs/\n.env\n'

    config=f"""const BOOTSTRAP: address = {BOOT};
const UPGRADE_DELAY: u32 = 720u32;
struct Settings {{ admin: address, upgrader: address, protocol_fee_bps: u16 }}
struct UpgradeKey {{ module: address, edition: u16 }}
program {C} {{
    mapping settings: bool => Settings;
    mapping pending_settings: bool => Settings;
    mapping upgrade_after: field => u32;
    fn initialize() -> Final {{
        assert_eq(std::ctx::caller(), BOOTSTRAP);
        return final {{
            assert(!settings.contains(true));
            settings.set(true, Settings {{ admin: BOOTSTRAP, upgrader: BOOTSTRAP, protocol_fee_bps: 0u16 }});
        }};
    }}
    fn set_admin(public admin: address, public upgrader: address) -> Final {{
        let caller = std::ctx::caller();
        return final {{
            assert_eq(settings.get(true).admin, caller);
            pending_settings.set(true, Settings {{ admin: admin, upgrader: upgrader, protocol_fee_bps: 0u16 }});
        }};
    }}
    fn accept_admin() -> Final {{
        let caller = std::ctx::caller();
        return final {{
            let pending = pending_settings.get(true);
            assert_eq(pending.admin, caller);
            settings.set(true, pending);
            pending_settings.remove(true);
        }};
    }}
    fn schedule_upgrade(public module: address, public edition: u16) -> Final {{
        assert(edition > 0u16);
        let caller = std::ctx::caller();
        let key = BHP256::hash_to_field(UpgradeKey {{ module: module, edition: edition }});
        return final {{
            assert_eq(settings.get(true).admin, caller);
            assert(!upgrade_after.contains(key));
            upgrade_after.set(key, std::ctx::block_height() + UPGRADE_DELAY);
        }};
    }}
    fn cancel_upgrade(public module: address, public edition: u16) -> Final {{
        let caller = std::ctx::caller();
        let key = BHP256::hash_to_field(UpgradeKey {{ module: module, edition: edition }});
        return final {{
            assert_eq(settings.get(true).admin, caller);
            upgrade_after.remove(key);
        }};
    }}
    // Upgrades require both the configured upgrader and an edition-specific delay.
{upgrade(True)}}}
"""
    write(C,config,[])
    hub=f'''import {C};
export struct MerkleProof {{ siblings: [field; 16], leaf_index: u32 }}
export struct Asset {{ program_id: identifier, token_id: field, family: u8, version: u16 }}
export struct AssetPolicy {{ family: u8, version: u16, enabled: bool }}
struct ModuleTag {{ module: address, tag: u8 }}
struct UpgradeKey {{ module: address, edition: u16 }}
program {H} {{
    mapping approved: field => bool;
    mapping assets: identifier => AssetPolicy;
    fn set_tag(public module: address, public tag: u8, public enabled: bool) -> Final {{
        assert(tag == 1u8 || tag == 2u8);
        let sender = std::ctx::caller();
        let key = BHP256::hash_to_field(ModuleTag {{ module: module, tag: tag }});
        return final {{
            assert_eq({C}::settings.get(true).admin, sender);
            approved.set(key, enabled);
        }};
    }}
    // A token's route is immutable once registered. Revocation only stops new exposure.
    fn set_asset(public token: identifier, public family: u8, public enabled: bool) -> Final {{
        assert(family >= 1u8 && family <= 3u8);
        assert_eq(token == 'credits', family == 1u8);
        let sender = std::ctx::caller();
        return final {{
            assert_eq({C}::settings.get(true).admin, sender);
            if assets.contains(token) {{
                let old = assets.get(token);
                assert_eq(old.family, family); assert_eq(old.version, 1u16);
            }}
            assets.set(token, AssetPolicy {{ family: family, version: 1u16, enabled: enabled }});
        }};
    }}
{upgrade()}}}
'''
    write(H,hub,[C])
    terms=f'''export struct Terms {{
    credit_asset: {H}::Asset, collateral_asset: {H}::Asset,
    min_draw: u128, max_draw: u128, collateral_ratio: u64, repayment_ratio: u64,
    accruing_apr: u32, duration: u32, expiry: u32, lender_auth: field,
}}
'''
    pre=f'import credits.aleo;\nimport {C};\nimport {H};\n'+AUTH+INTERFACES+MATH+shared_logic(H)
    proposal=pre+terms+proposal_logic(C,H,P)+f'''program {P} {{
    mapping terms_hash: field => field;
    mapping credit_assets: field => {H}::Asset;
    mapping available_credit: field => u128;
    mapping repayments: field => u128;
    mapping closed: field => bool;
    mapping liabilities: identifier => u128;
'''
    for k in FAMILIES:
        a='terms.credit_asset'
        proposal+=f'''
    fn open_{k}(public nonce: field, public terms: Terms, input: {rec(k)}, public amount: u128, salt: field{proof(k)})
        -> {sig([k],[rec(k),'public field','Final'])} {{
        {family(k,a)}
        validate_open_terms(terms, amount, salt);
        let id = {pos(1,P,'terms.lender_auth')};
        let hash = BHP256::hash_to_field(terms);
        let product = BHP256::hash_to_field(ModuleTag {{ module: std::ctx::addr(), tag: 2u8 }});
        {deposit(k,a,'amount','input')}
        return ({outputs([(k,'compliance')],['change','id'])}, final {{
            validate_open(product, terms, id);
            let total = liabilities.get_or_use({a}.program_id, 0u128);
            {before(k,a)}
            register_commitment(id, hash, {a}, amount, total);
            deposit.run();
            {after(k,a,'amount','+')}
        }});
    }}
    fn draw_{k}(public id: field, public terms: Terms, public amount: u128, recipient: address)
        -> {sig([k],[rec(k),'Final'])} {{
        assert_eq(std::ctx::caller(), {L}); {family(k,a)}
        assert_eq(recipient, std::ctx::signer());
        assert(amount >= terms.min_draw && amount <= terms.max_draw);
        let hash = BHP256::hash_to_field(terms);
        let loan = BHP256::hash_to_field(ModuleTag {{ module: {L}, tag: 1u8 }});
        let product = BHP256::hash_to_field(ModuleTag {{ module: std::ctx::addr(), tag: 2u8 }});
        {payout(k,a,'amount','recipient')}
        return ({outputs([(k,'compliance')],['output'])}, final {{
            validate_draw(loan, product, terms, id, hash);
            let total = liabilities.get({a}.program_id); {before(k,a)}
            debit_draw(id, {a}.program_id, amount, total);
            payout.run(); {after(k,a,'amount','-')}
        }});
    }}
    fn receive_{k}(public id: field, public asset: {H}::Asset, input: {rec(k)}, public amount: u128{proof(k)})
        -> {sig([k],[rec(k),'Final'])} {{
        assert_eq(std::ctx::caller(), {L}); {family(k,'asset')}
        {deposit(k,'asset','amount','input')}
        return ({outputs([(k,'compliance')],['change'])}, final {{
            assert_eq(credit_assets.get(id), asset);
            let total = liabilities.get(asset.program_id); let before = {balance(k,'asset')};
            credit_repayment(id, asset.program_id, amount, total);
            deposit.run(); {after(k,'asset','amount','+')}
        }});
    }}
'''
        for op in ['cancel','withdraw']:
            check='cancel_available(id, amount);' if op=='cancel' else 'repayments.set(id, repayments.get(id) - amount);'
            proposal+=f'''
    fn {op}_{k}(public id: field, public terms: Terms, salt: field, public amount: u128)
        -> {sig([k],[rec(k),'Final'])} {{
        {family(k,a)}
        {'assert(amount > 0u128);' if op=='withdraw' else ''}
        assert_eq(terms.lender_auth, {auth(1,P,'salt')});
        let hash = BHP256::hash_to_field(terms);
        {payout(k,a,'amount','std::ctx::signer()')}
        return ({outputs([(k,'compliance')],['output'])}, final {{
            assert_eq(terms_hash.get(id), hash);
            let total = liabilities.get({a}.program_id); {before(k,a)}
            {check}
            liabilities.set({a}.program_id, total - amount);
            payout.run(); {after(k,a,'amount','-')}
        }});
    }}
'''
    write(P,proposal+upgrade()+'}\n',['credits.aleo',C,H])
    loan=pre+f'import {P};\n'+f'''export struct Loan {{
    loan_id: field, commitment_id: field,
    credit_asset: {H}::Asset, collateral_asset: {H}::Asset,
    credit_amount: u128, collateral_amount: u128, repayment_amount: u128,
    accruing_apr: u32, borrower_auth: field, lender_auth: field,
}}
struct State {{ witness_hash: field, maturity: u32, start: i64, status: u8 }}
{loan_logic(P)}program {L} {{
    mapping loans: field => State;
    mapping liabilities: identifier => u128;
'''
    for c in FAMILIES:
        for k in FAMILIES:
            a='witness.collateral_asset'
            loan+=f'''
    fn accept_{c}_{k}(public nonce: field, public commitment_id: field, public terms: {P}::Terms,
        public credit_amount: u128, collateral: {rec(k)}, borrower_salt: field{proof(k)})
        -> {sig([k,c],[rec(c),rec(k),'public Loan','Final'])} {{
        {family(c,'terms.credit_asset')} {family(k,'terms.collateral_asset')}
        let collateral_amount = rounded(credit_amount, terms.collateral_ratio);
        let repayment_amount = rounded(credit_amount, terms.repayment_ratio);
        let (id, witness) = make_loan::[{L}](nonce, commitment_id, terms, credit_amount, collateral_amount, repayment_amount, borrower_salt);
        let hash = BHP256::hash_to_field(witness);
        {deposit(k,'terms.collateral_asset','collateral_amount','collateral','lock')}
        let ({outputs([(c,'credit_compliance')],['credit','draw'])}) = {P}::draw_{c}(commitment_id, terms, credit_amount, std::ctx::signer());
        return ({outputs([(k,'compliance'),(c,'credit_compliance')],['credit','change','witness'])}, final {{
            assert(!loans.contains(id));
            let total = liabilities.get_or_use({a}.program_id, 0u128); {before(k,a)}
            register_loan(id, witness, hash, terms, collateral_amount, total);
            lock.run(); {after(k,a,'collateral_amount','+')}
            draw.run();
        }});
    }}
    fn repay_{c}_{k}(public witness: Loan, input: {rec(c)}, public amount: u128, borrower_salt: field{proof(c)})
        -> {sig([c,k],[rec(c),rec(k),'Final'])} {{
        {family(c,'witness.credit_asset')} {family(k,a)}
        let hash = repayment_witness_hash::[{L}](witness, amount, borrower_salt);
        let ({outputs([(c,'credit_compliance')],['change','pay'])}) = {P}::receive_{c}(witness.commitment_id, witness.credit_asset, input, amount{', proofs' if c=='compliant' else ''});
        {payout(k,a,'witness.collateral_amount','std::ctx::signer()','release','collateral','collateral_compliance')}
        return ({outputs([(c,'credit_compliance'),(k,'collateral_compliance')],['change','collateral'])}, final {{
            let state = validate_repayment(witness, hash, amount);
            let total = liabilities.get({a}.program_id); {before(k,a)}
            settle_loan::[2u8](witness, hash, state, total);
            pay.run(); release.run(); {after(k,a,'witness.collateral_amount','-')}
        }});
    }}
'''
    for k in FAMILIES:
        a='witness.collateral_asset'
        loan+=f'''
    fn claim_{k}(public witness: Loan, lender_salt: field) -> {sig([k],[rec(k),'Final'])} {{
        {family(k,a)}
        assert_eq(witness.lender_auth, {auth(1,P,'lender_salt')});
        let hash = BHP256::hash_to_field(witness);
        {payout(k,a,'witness.collateral_amount','std::ctx::signer()','release','collateral')}
        return ({outputs([(k,'compliance')],['collateral'])}, final {{
            let state = validate_default(witness, hash);
            let total = liabilities.get({a}.program_id); {before(k,a)}
            settle_loan::[3u8](witness, hash, state, total);
            release.run(); {after(k,a,'witness.collateral_amount','-')}
        }});
    }}
'''
    write(L,loan+upgrade()+'}\n',['credits.aleo',C,H,P])
    return files


def generate(root=ROOT):
    for relative, content in render_programs().items():
        path = Path(root) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    print('Generated pwn_config_poc/pwn_hub_poc/pwn_proposal_poc/pwn_loan_poc: native, ARC-20, deployed-compliance ABI; nine family pairs.')
if __name__=='__main__':generate()
