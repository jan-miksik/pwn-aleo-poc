"""Isolated local experiment: public USDCx allowance + private native collateral.

NOT a lending product: public quotes and a borrower-only test refund. It has no
interest/default logic and is never imported by the production PoC programs.
"""
import json

NAME = 'pwn_allowance_probe'
SOURCE = '''import credits.aleo;
import usdcx_stablecoin.aleo;
struct Quote { lender: address, borrower: address, principal: u128, collateral: u64, expiry: u32 }
program pwn_allowance_probe.aleo {
    mapping quotes: field => field;
    mapping status: field => u8;
    mapping reserved: bool => u64;
    fn authorize(public id: field, public quote: Quote) -> Final {
        assert_eq(std::ctx::signer(), quote.lender);
        assert(quote.principal > 0u128 && quote.collateral > 0u64);
        let hash = BHP256::hash_to_field(quote);
        return final {
            assert(!quotes.contains(id)); assert(std::ctx::block_height() < quote.expiry);
            quotes.set(id, hash); status.set(id, 0u8);
        };
    }
    fn cancel(public id: field, public quote: Quote) -> Final {
        assert_eq(std::ctx::signer(), quote.lender);
        let hash = BHP256::hash_to_field(quote);
        return final {
            assert_eq(quotes.get(id), hash); assert_eq(status.get(id), 0u8);
            status.set(id, 2u8);
        };
    }
    fn accept(public id: field, public quote: Quote, collateral: credits.aleo::credits)
        -> (credits.aleo::credits, usdcx_stablecoin.aleo::ComplianceRecord, usdcx_stablecoin.aleo::Token, Final) {
        assert_eq(std::ctx::signer(), quote.borrower);
        let hash = BHP256::hash_to_field(quote);
        let (change, lock) = credits.aleo::transfer_private_to_public(collateral, std::ctx::addr(), quote.collateral);
        let (receipt, credit, draw) = usdcx_stablecoin.aleo::transfer_from_public_to_private(quote.lender, quote.borrower, quote.principal);
        return (change, receipt, credit, final {
            assert_eq(quotes.get(id), hash); assert_eq(status.get(id), 0u8);
            assert(std::ctx::block_height() < quote.expiry);
            let total = reserved.get_or_use(true, 0u64);
            let before = credits.aleo::account.get_or_use(std::ctx::addr(), 0u64);
            assert(before >= total);
            status.set(id, 1u8); reserved.set(true, total + quote.collateral);
            lock.run();
            assert_eq(credits.aleo::account.get(std::ctx::addr()), before + quote.collateral);
            draw.run();
        });
    }
    // Test cleanup only. A production loan would require repayment/default settlement.
    fn refund(public id: field, public quote: Quote) -> (credits.aleo::credits, Final) {
        assert_eq(std::ctx::signer(), quote.borrower);
        let hash = BHP256::hash_to_field(quote);
        let (output, pay) = credits.aleo::transfer_public_to_private(quote.borrower, quote.collateral);
        return (output, final {
            assert_eq(quotes.get(id), hash); assert_eq(status.get(id), 1u8);
            let total = reserved.get(true);
            let before = credits.aleo::account.get(std::ctx::addr()); assert(before >= total);
            reserved.set(true, total - quote.collateral); status.set(id, 3u8);
            pay.run(); assert_eq(credits.aleo::account.get(std::ctx::addr()), before - quote.collateral);
        });
    }
    @noupgrade constructor() {}
}
'''


def stage(base):
    directory=base/NAME
    (directory/'src').mkdir(parents=True,exist_ok=True)
    (directory/'src/main.leo').write_text(SOURCE)
    (directory/'program.json').write_text(json.dumps(dict(
        program=NAME+'.aleo',version='0.1.0',description='LOCAL EXPERIMENT ONLY',
        license='GPL-3.0-only',leo='4.4.2',dependencies=[
            dict(name=n+'.aleo',location='local',path='../vendor/'+n+'.aleo',edition=None)
            for n in ('credits','merkle_tree','usdcx_multisig_core','usdcx_freezelist','usdcx_stablecoin')]),indent=2)+'\n')


def run(t):
    program=NAME+'.aleo';token='usdcx_stablecoin.aleo';x=t.execute
    quote=f'{{ lender: {t.DEV}, borrower: {t.B}, principal: 400u128, collateral: 600u64, expiry: {t.height()+1000}u32 }}'
    x(token+'::mint_public',[t.DEV,'1200u128'])
    balance=t.mapping(token,'balances',t.DEV)
    x(program+'::authorize',['1field',quote])
    x(token+'::approve_public',[program,'800u128'])
    t.check('posting and approval do not transfer principal or collateral',
            t.mapping(token,'balances',t.DEV)==balance
            and t.mapping('credits.aleo','account',program) in (None,'0u64'))
    record=t.private('aleo',1000,t.B,t.BK)
    args=['1field',quote,record]
    before=lambda: [t.mapping(program,'status','1field'),t.mapping(program,'reserved','true'),
                    t.mapping('credits.aleo','account',program),t.mapping(token,'balances',t.DEV)]
    unchanged=before()
    x(program+'::accept',['1field',quote,t.private('aleo',1000)],fail=True)
    x(program+'::accept',['1field',quote.replace('400u128','401u128'),record],t.BK,True)
    t.check('quote owner/recipient/amount are enforced atomically',unchanged==before())
    x(token+'::unapprove_public',[program,'800u128'])
    unchanged=before();x(program+'::accept',args,t.BK,True)
    t.check('revoked allowance rolls back collateral and loan creation',unchanged==before())
    x(token+'::approve_public',[program,'800u128'])
    x(token+'::burn_public',[t.DEV,'1000u128'])
    unchanged=before();x(program+'::accept',args,t.BK,True)
    t.check('insufficient lender balance rolls back collateral and loan creation',unchanged==before())
    x(token+'::mint_public',[t.DEV,'1000u128'])
    x(program+'::accept',args,t.BK,prove=True)
    t.check('allowance funds credit at atomic loan creation',
            t.mapping(program,'status','1field')=='1u8'
            and t.mapping('credits.aleo','account',program)=='600u64'
            and t.mapping(token,'balances',t.DEV)=='800u128')
    t.decrypt_payout('usdcx',400,t.BK,t.B,function='transfer_from_public_to_private')
    x(program+'::accept',['1field',quote,t.private('aleo',1000,t.B,t.BK)],t.BK,True)
    x(program+'::refund',['1field',quote],t.BK)
    t.check('test-only refund clears experimental collateral',t.mapping(program,'reserved','true')=='0u64')
    x(program+'::authorize',['2field',quote]);x(program+'::cancel',['2field',quote])
    x(program+'::accept',['2field',quote,t.private('aleo',1000,t.B,t.BK)],t.BK,True)
    expired=quote.replace(quote.split('expiry: ')[1].split('u32')[0],str(t.height()-1))
    x(program+'::authorize',['3field',expired],fail=True)
