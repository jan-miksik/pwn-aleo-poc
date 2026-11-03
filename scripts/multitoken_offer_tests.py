"""Bidirectional offer scenarios using the existing local devnode harness."""
import json
import re


def shared_terms(t, c, k, salt, direction, owner, duration=1000, minimum=100,
                 maximum=600, ratio=15000, apr=0):
    return (f'{{ direction: {direction}u8, credit_asset: {t.asset(c)}, collateral_asset: {t.asset(k)}, '
            f'min_draw: {minimum}u128, max_draw: {maximum}u128, collateral_ratio: {ratio}u64, '
            f'repayment_ratio: 11000u64, accruing_apr: {apr}u32, duration: {duration}u32, '
            f'expiry: {t.height()+5000}u32, maker_auth: {t.auth(salt,owner,direction)} }}')


def opening(owner, taker, salt):
    return f'{{ recipient: {owner}, taker: {taker}, salt: {salt}field }}'


def legacy_terms(terms):
    return re.sub(r'direction: \d+u8,\s*', '', terms).replace('maker_auth:', 'lender_auth:')


def public_execution(t):
    tx = t.rpc('transaction/' + t.LAST['transaction_id'])
    return json.dumps(tx['execution'])


def privacy(t, program, mapping, cid, secret_markers):
    public = public_execution(t)
    t.check('private offer has no public terms listing', t.mapping(program, mapping, cid) is None)
    for marker in secret_markers:
        t.check('private opening omits secret from public execution: ' + marker[:22],
                marker not in public)


def snapshot(t, cid, c, k):
    def reserve(asset):
        token, family = t.ASSETS[asset]
        return t.mapping('credits.aleo' if family == 1 else token+'.aleo',
                         'account' if family == 1 else 'balances', t.L)
    return [t.mapping(t.L, name, cid) for name in
            ('borrow_hashes', 'borrow_remaining', 'borrow_collateral', 'borrow_expiry', 'borrow_closed')] + [
                t.mapping(t.L, 'liabilities', f"'{t.ASSETS[k][0]}'"), reserve(c), reserve(k)]


def open_borrow(t, c, k, salt, private_offer, requested=1000, collateral=1500, **terms_options):
    ts = shared_terms(t,c,k,salt,2,t.B,**terms_options)
    op = opening(t.B,t.DEV,salt+100000)
    offer = t.offer_witness(ts,op,private_offer)
    cid = t.execute(t.L+'::open_borrow_'+t.route(k), [
        '1field',t.module_id(t.P),t.empty_terms() if private_offer else ts,offer,
        t.private(k,collateral,t.B,t.BK),
        f'{{ requested: {requested}u128, collateral: {collateral}u128 }}',f'{salt}field'
    ]+t.proofs(k),t.BK)[-2]
    return ts,op,offer,cid


def fill_borrow(t,c,offer,cid,salt,amount=400,nonce=1,key=None,owner=None,
                fail=False,prove=False,record=None):
    key=key or t.AK;owner=owner or t.DEV
    out=t.execute(t.L+'::accept_borrow_'+t.route(c), [
        f'{nonce}field',t.module_id(t.P),cid,offer,record or t.private(c,amount,owner,key),
        f'{amount}u128',f'{salt}field'
    ]+t.proofs(c),key,fail,prove)
    return None if fail else out[-2]


def cancel_borrow(t,k,offer,cid,salt,amount,fail=False):
    return t.execute(t.L+'::cancel_borrow_'+t.route(k), [
        cid,t.module_id(t.P),offer,f'{salt}field',f'{amount}u128'
    ],t.BK,fail)


def settle(t,c,k,w,borrower_salt,lender_salt,key=None,amount=440):
    t.execute(t.L+'::repay_'+t.route(c)+'_'+t.route(k),[
        w,t.private(c,amount,t.B,t.BK),f'{amount}u128',f'{borrower_salt}field'
    ]+t.proofs(c),t.BK)
    t.decrypt_payout(k,int(re.search(r'collateral_amount:\s*(\d+)u128',w)[1]),t.BK,t.B)
    t.execute(t.P+'::withdraw_loan_'+t.route(c),[w,f'{lender_salt}field',f'{amount}u128'],key or t.AK)


def run(t):
    # Deterministic, public seed: this is a third LOCAL TEST account, never a real wallet.
    code,log=t.cli(['account','new','--seed','20261102'],'third-test-account')
    assert code==0,log[-1500:]
    # Leo 4.4.2 advertises --json-output here but only emits account text.
    ck=re.search(r'APrivateKey1[0-9A-Za-z]+',log)[0]
    third=re.search(r'aleo1[0-9a-z]+',log)[0]
    t.execute('credits.aleo::transfer_public',[third,'1000000000u64'])
    salt=9000
    for private_offer in (False,True):
        for c in ('aleo','sol','usdcx'):
            for k in ('aleo','wbtc','usad'):
                salt+=1
                ts,op,offer,cid=open_borrow(t,c,k,salt,private_offer,apr=23456)
                if private_offer:
                    privacy(t,t.L,'borrow_public_terms',cid,
                            ['23456u32',f'{salt+100000}field',t.B,t.DEV])
                else:
                    t.check('public borrower terms are discoverable',
                            'direction: 2u8' in t.mapping(t.L,'borrow_public_terms',cid))
                w1=fill_borrow(t,c,offer,cid,salt+1000,
                               prove=private_offer and c=='aleo' and k=='aleo')
                t.spend_payout(c,400,t.BK,t.B)
                # Private offers deliberately retain one designated counterparty.
                lender_key=t.AK if private_offer else ck
                lender_owner=t.DEV if private_offer else third
                w2=fill_borrow(t,c,offer,cid,salt+2000,nonce=2,key=lender_key,owner=lender_owner)
                t.decrypt_payout(c,400,t.BK,t.B)
                t.check('borrower multi-fill reserves are partitioned',
                        t.mapping(t.L,'borrow_remaining',cid)=='200u128'
                        and t.mapping(t.L,'borrow_collateral',cid)=='300u128'
                        and t.mapping(t.L,'liabilities',f"'{t.ASSETS[k][0]}'")=='1500u128'
                        and t.lid(w1)!=t.lid(w2))
                before=snapshot(t,cid,c,k)
                fill_borrow(t,c,offer,cid,salt+3000,amount=300,nonce=3,fail=True)
                t.check('overfill rolls back all reserve and offer state',before==snapshot(t,cid,c,k))
                cancel_borrow(t,k,offer,cid,salt,300)
                t.decrypt_payout(k,300,t.BK,t.B)
                t.check('cancellation protects both active loans',
                        t.mapping(t.L,'liabilities',f"'{t.ASSETS[k][0]}'")=='1200u128')
                # Repay one lender, then demonstrate that the other cannot withdraw its proceeds.
                t.repay(c,k,w1,salt)
                t.execute(t.P+'::withdraw_loan_'+t.route(c),[w1,f'{salt+2000}field','440u128'],lender_key,True)
                t.execute(t.P+'::withdraw_loan_'+t.route(c),[w1,f'{salt+1000}field','440u128'])
                t.decrypt_payout(c,440,t.AK,t.DEV)
                settle(t,c,k,w2,salt,salt+2000,lender_key)
                t.decrypt_payout(c,440,lender_key,lender_owner)
                t.check(f'{c}/{k} borrower {"private" if private_offer else "public"} clears all liabilities',
                        t.mapping(t.L,'liabilities',f"'{t.ASSETS[k][0]}'")=='0u128'
                        and t.mapping(t.P,'liabilities',f"'{t.ASSETS[c][0]}'")=='0u128'
                        and t.mapping(t.L,'borrow_remaining',cid)=='0u128')
    # Every family pair also exercises private lender openings and repeated acceptance.
    for c in ('aleo','sol','usdcx'):
        for k in ('aleo','wbtc','usad'):
            salt+=1
            ts=shared_terms(t,c,k,salt,1,t.DEV,apr=23456)
            op=opening(t.DEV,t.B,salt+100000);offer=t.offer_witness(ts,op,True)
            cid=t.execute(t.P+'::open_private_'+t.route(c),[
                '1field',ts,op,t.private(c,1000),'1000u128',f'{salt}field'
            ]+t.proofs(c))[-2]
            privacy(t,t.P,'offer_terms',cid,['23456u32',f'{salt+100000}field',t.B,t.DEV])
            ws=[]
            for n in (1,2):
                args=t.accept_args(k,legacy_terms(ts),cid,salt+1000+n,nonce=n,offer=offer)
                ws.append(t.execute(t.L+'::accept_'+t.route(c)+'_'+t.route(k),args,t.BK)[-2])
                t.decrypt_payout(c,400,t.BK,t.B)
            t.execute(t.P+'::cancel_private_'+t.route(c),[cid,ts,op,f'{salt}field','200u128'])
            for n,w in enumerate(ws,1):t.repay(c,k,w,salt+1000+n)
            t.execute(t.P+'::withdraw_private_'+t.route(c),[cid,ts,op,f'{salt}field','880u128'])
            t.decrypt_payout(c,880)
            t.check('private lender multi-fill retains non-revolving capacity',
                    t.mapping(t.P,'available_credit',cid)=='0u128'
                    and t.mapping(t.P,'liabilities',f"'{t.ASSETS[c][0]}'")=='0u128')
    adversarial(t,third,ck)


def adversarial(t,third,ck):
    c,k='sol','usad';salt=12000
    ts,op,offer,cid=open_borrow(t,c,k,salt,True,duration=100)
    before=snapshot(t,cid,c,k)
    fill_borrow(t,c,offer,cid,13000,key=ck,owner=third,fail=True)
    fill_borrow(t,c,offer.replace('private_offer: true','private_offer: false'),cid,13000,key=ck,owner=third,fail=True)
    fill_borrow(t,c,offer.replace('recipient: '+t.B,'recipient: '+third),cid,13000,fail=True)
    fill_borrow(t,c,offer.replace('repayment_ratio: 11000u64','repayment_ratio: 10000u64'),cid,13000,fail=True)
    fill_borrow(t,c,offer,cid,13000,amount=99,fail=True)
    fill_borrow(t,c,offer,cid,13000,amount=601,fail=True)
    t.check('unauthorized and modified borrower fills leave state unchanged',before==snapshot(t,cid,c,k))
    w1=fill_borrow(t,c,offer,cid,13000)
    w2=fill_borrow(t,c,offer,cid,14000,nonce=2)
    before=snapshot(t,cid,c,k)
    fill_borrow(t,c,offer,cid,13000,fail=True)
    t.check('replayed fill cannot reserve more collateral',before==snapshot(t,cid,c,k))
    cancel_borrow(t,k,offer,cid,salt,300)
    fill_borrow(t,c,offer,cid,15000,amount=100,nonce=3,fail=True)
    t.execute(t.L+'::claim_'+t.route(k),[w1,'13000field'],fail=True)
    # At maturity: repay one loan, default the other, then reject both second settlements.
    for _ in range(101):t.rpc('block/create',{})
    t.repay(c,k,w1,salt)
    t.execute(t.L+'::claim_'+t.route(k),[w1,'13000field'],fail=True)
    t.execute(t.P+'::withdraw_loan_'+t.route(c),[w1,'13000field','440u128'])
    t.execute(t.L+'::claim_'+t.route(k),[w2,'14000field'])
    t.spend_payout(k,600)
    t.repay(c,k,w2,salt,True)
    t.execute(t.L+'::claim_'+t.route(k),[w2,'14000field'],fail=True)
    t.check('mixed repayment/default is isolated per borrower fill',
            t.mapping(t.L,'liabilities',"'usad_stablecoin'")=='0u128')
    # Rounded per-loan collateral may leave an unfillable remainder; never round a loan down.
    ts,op,offer,cid=open_borrow(t,'sol','wbtc',12001,False,requested=3,collateral=5,
                              minimum=1,maximum=3,ratio=15001)
    a=fill_borrow(t,'sol',offer,cid,13001,amount=1)
    b=fill_borrow(t,'sol',offer,cid,13002,amount=1,nonce=2)
    before=snapshot(t,cid,'sol','wbtc')
    fill_borrow(t,'sol',offer,cid,13003,amount=1,nonce=3,fail=True)
    t.check('rounding cannot borrow another loan collateral',before==snapshot(t,cid,'sol','wbtc'))
    cancel_borrow(t,'wbtc',offer,cid,12001,1)
    settle(t,'sol','wbtc',a,12001,13001,amount=2)
    settle(t,'sol','wbtc',b,12001,13002,amount=2)
    t.check('rounding remainder and both loan reserves fully clear',
            t.mapping(t.L,'liabilities',"'arc20_wbtc'")=='0u128')


def extra_security(t):
    """Run in the security suite, including rejected-transaction disclosure checks."""
    code,log=t.cli(['account','new','--seed','20261102'],'third-test-account')
    assert code==0
    ck=re.search(r'APrivateKey1[0-9A-Za-z]+',log)[0]
    third=re.search(r'aleo1[0-9a-z]+',log)[0]
    t.execute('credits.aleo::transfer_public',[third,'1000000000u64'])
    c,k='sol','usad'
    # A public lender offer genuinely serves two different borrowers.
    ts,cid=t.open_(c,k,18000)
    first=t.accept(c,k,ts,cid,19000)
    second=t.execute(t.L+'::accept_arc20_compliant',
                     t.accept_args(k,ts,cid,19001,nonce=2,collateral=t.private(k,1000,third,ck)),ck)[-2]
    t.decrypt_payout(c,400,ck,third)
    t.repay(c,k,first,19000)
    t.execute(t.L+'::repay_arc20_compliant',[
        second,t.private(c,440,third,ck),'440u128','19001field']+t.proofs(c),ck)
    t.decrypt_payout(k,600,ck,third)
    t.execute(t.P+'::cancel_arc20',[cid,ts,'18000field','200u128'])
    t.execute(t.P+'::withdraw_arc20',[cid,ts,'18000field','880u128'])
    t.check('public lender multiple fills support independent borrowers',
            t.lid(first)!=t.lid(second) and t.mapping(t.L,'liabilities',"'usad_stablecoin'")=='0u128')
    # Private lender authorization, immutable terms and public-mode bypass.
    ts=shared_terms(t,c,k,18001,1,t.DEV,minimum=123,maximum=789,apr=23456)
    op=opening(t.DEV,t.B,918001);offer=t.offer_witness(ts,op,True)
    cid=t.execute(t.P+'::open_private_arc20',[
        '1field',ts,op,t.private(c,1000),'1000u128','18001field'])[-2]
    privacy(t,t.P,'offer_terms',cid,['23456u32','918001field',t.DEV,t.B])
    args=t.accept_args(k,legacy_terms(ts),cid,19002,offer=offer,
                       collateral=t.private(k,1000,third,ck))
    t.execute(t.L+'::accept_arc20_compliant',args,ck,True)
    args=t.accept_args(k,legacy_terms(ts),cid,19002,offer=offer)
    changed=args.copy();changed[3]=changed[3].replace('440u128','400u128')
    t.execute(t.L+'::accept_arc20_compliant',changed,t.BK,True)
    bypass=args.copy();bypass[4]=offer.replace('private_offer: true','private_offer: false')
    t.execute(t.L+'::accept_arc20_compliant',bypass,t.BK,True)
    # A finalized rejection still publishes the submitted LoanTerms, but not the opening.
    receipt=t.rpc('transaction/confirmed/'+t.LAST['transaction_id'])
    rejected=receipt.get('rejected',{}).get('execution')
    assert receipt.get('status')=='rejected' and rejected,'Missing published rejected execution'
    public=json.dumps(rejected)
    t.check('rejected acceptance discloses submitted loan rate', '23456u32' in public)
    t.check('rejected acceptance keeps complete opening private',
            '918001field' not in public and '789u128' not in public and t.DEV not in public)
    t.execute(t.P+'::cancel_private_arc20',[cid,ts,op,'18001field','1000u128'],ck,True)
    w=t.execute(t.L+'::accept_arc20_compliant',args,t.BK)[-2]
    t.execute(t.P+'::cancel_private_arc20',[cid,ts,op,'18001field','600u128'])
    t.repay(c,k,w,19002)
    t.execute(t.P+'::withdraw_private_arc20',[cid,ts,op,'18001field','440u128'])
    # Borrower expiry and revocation block new exposure, not cancellation/settlement.
    ts,op,offer,cid=open_borrow(t,c,k,18002,True,duration=100)
    w=fill_borrow(t,c,offer,cid,19003)
    t.execute(t.H+'::set_offer_module',[t.module_id(t.P),'false'])
    t.execute(t.H+'::set_tag',[t.L,'1u8','false'])
    fill_borrow(t,c,offer,cid,19004,nonce=2,fail=True)
    cancel_borrow(t,k,offer,cid,18002,900)
    settle(t,c,k,w,18002,19003)
    t.check('borrower exits survive module revocation',
            t.mapping(t.L,'liabilities',"'usad_stablecoin'")=='0u128')
    t.execute(t.H+'::set_offer_module',[t.module_id(t.P),'true'])
    t.execute(t.H+'::set_tag',[t.L,'1u8','true'])
    # An expired committed offer cannot fill, but its maker can recover all collateral.
    ts=shared_terms(t,c,k,18003,2,t.B)
    ts=re.sub(r'expiry: \d+u32',f'expiry: {t.height()+20}u32',ts)
    op=opening(t.B,t.DEV,918003);offer=t.offer_witness(ts,op,False)
    cid=t.execute(t.L+'::open_borrow_compliant',[
        '1field',t.module_id(t.P),ts,offer,t.private(k,1500,t.B,t.BK),
        '{ requested: 1000u128, collateral: 1500u128 }','18003field']+t.proofs(k),t.BK)[-2]
    for _ in range(21):t.rpc('block/create',{})
    fill_borrow(t,c,offer,cid,19005,fail=True)
    cancel_borrow(t,k,offer,cid,18003,1500)
    t.check('expired borrower offer refunds unused collateral',
            t.mapping(t.L,'liabilities',"'usad_stablecoin'")=='0u128')
