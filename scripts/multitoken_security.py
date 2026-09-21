"""Adversarial and lifecycle cases for the local runner."""


def validate_terms_regressions(t):
    """Every public open route must retain the extracted economic checks."""
    invalid_terms = (
        ('min_draw: 100u128', 'min_draw: 0u128'),
        ('max_draw: 600u128', 'max_draw: 99u128'),
        ('collateral_ratio: 15000u64', 'collateral_ratio: 0u64'),
        ('collateral_ratio: 15000u64', 'collateral_ratio: 1000001u64'),
        ('repayment_ratio: 11000u64', 'repayment_ratio: 9999u64'),
        ('repayment_ratio: 11000u64', 'repayment_ratio: 1000001u64'),
        ('accruing_apr: 0u32', 'accruing_apr: 100001u32'),
        ('duration: 1000u32', 'duration: 9u32'),
        ('duration: 1000u32', 'duration: 3153601u32'),
    )
    for index, credit in enumerate(('aleo', 'sol', 'usdcx')):
        salt = 8000 + index
        terms = t.terms(credit, 'wbtc', salt)
        deposit = t.private(credit, 1000)
        function = t.P + '::open_' + t.route(credit)
        for original, invalid in invalid_terms:
            assert terms.count(original) == 1
            t.execute(function, ['1field', terms.replace(original, invalid), deposit,
                                 '1000u128', f'{salt}field'] + t.proofs(credit), fail=True)
        # The same deposit record and position ID remain usable after rejection.
        cid = t.execute(function, ['1field', terms, deposit, '1000u128', f'{salt}field']
                        + t.proofs(credit))[-2]
        t.execute(t.P + '::cancel_' + t.route(credit), [cid, terms, f'{salt}field', '1000u128'])
        t.check(credit + ' open-term checks reject invalid economics without consuming the deposit',
                t.mapping(t.P, 'closed', cid) == 'true'
                and t.mapping(t.P, 'liabilities', f"'{t.ASSETS[credit][0]}'") == '0u128')


def run(t):
    validate_terms_regressions(t)
    X=t.execute; C=t.C; P=t.P; L=t.L; H=t.H; B=t.B; BK=t.BK
    # Governance uses the immediate caller and a two-step handover.
    X('pwn_local_fixture.aleo::forward_set_asset',["'credits'",'1u8','false'],fail=True)
    X('pwn_local_fixture.aleo::forward_set_admin',[B,B],fail=True)
    X(C+'::set_admin',[B,B])
    t.check('admin proposal does not transfer control',t.mapping(C,'settings','true').count(t.DEV)==2)
    X(C+'::accept_admin',[],BK)
    t.check('pending admin explicitly accepts control',t.mapping(C,'settings','true').count(B)==2)
    X(C+'::set_admin',[t.DEV,t.DEV],BK)
    X(C+'::accept_admin')
    t.check('two-step admin handover can be restored',t.mapping(C,'settings','true').count(t.DEV)==2)
    # Authorization and admission: no route spoofing, no retroactive rerouting.
    X(H+'::set_asset',["'arc20_sol'",'2u8','false'],BK,True)
    X(H+'::set_asset',["'arc20_sol'",'3u8','true'],fail=True)
    X(H+'::set_asset',["'credits'",'2u8','true'],fail=True)
    X(H+'::set_asset',["'arc20_sol'",'1u8','true'],fail=True)
    ts,cid=t.open_('sol','usad',901)
    w=t.accept('sol','usad',ts,cid,1901)
    X(P+'::draw_arc20',[cid,ts,'100u128',B],BK,True)
    X(P+'::receive_arc20',[cid,t.asset('sol'),t.private('sol',500),'440u128'],fail=True)
    t.repay('sol','usad',w,999,True)
    t.repay('sol','usad',w.replace('repayment_amount: 440u128','repayment_amount: 1u128'),1901,True)
    X(L+'::claim_compliant',[w,'901field'],fail=True)
    # Token substitution must fail even when shape/amount/owner are otherwise identical.
    # The binding of a record to its program is enforced by the execution proof (record commitment
    # and ledger inclusion), which a proof-skipping devnode does not see: this case is proved for real.
    X(L+'::repay_arc20_compliant',[w,t.private('wbtc',500,B,BK),'440u128','1901field'],BK,True,prove=True)
    t.check('substituted token cannot settle loan','status: 1u8' in t.mapping(L,'loans',t.lid(w)))
    # Disable new exposure, then prove that old positions still settle/refund.
    X(H+'::set_asset',["'arc20_sol'",'2u8','false'])
    X(H+'::set_asset',["'usad_stablecoin'",'3u8','false'])
    X(L+'::accept_arc20_compliant',['2field',cid,ts,'100u128',t.private('usad',200,B,BK),'1902field',t.PROOFS],BK,True)
    X(P+'::open_arc20',['2field',ts,t.private('sol',1000),'1000u128','901field'],fail=True)
    X(H+'::set_tag',[P,'2u8','false']);X(H+'::set_tag',[L,'1u8','false'])
    t.repay('sol','usad',w,1901,prove=True) # Same route, genuine record: proves the proving path itself works.
    t.check('genuine repayment proves and settles',t.PROVED[-1]['accepted'])
    t.spend_payout('usad',600,BK,B)
    X(P+'::withdraw_arc20',[cid,ts,'901field','440u128']);X(P+'::cancel_arc20',[cid,ts,'901field','600u128'])
    t.repay('sol','usad',w,1901,True)
    t.check('delisting and module pause preserve existing settlement',t.mapping(P,'liabilities',"'arc20_sol'")=='0u128')
    X(H+'::set_asset',["'arc20_sol'",'2u8','true']);X(H+'::set_asset',["'usad_stablecoin'",'3u8','true'])
    X(H+'::set_tag',[P,'2u8','true']);X(H+'::set_tag',[L,'1u8','true'])
    # All nine family combinations exercise the default route. Once claim wins,
    # repayment must lose through the shared status transition.
    salt=1000
    for c in ['aleo','sol','usdcx']:
        for k in ['aleo','wbtc','usad']:
            salt+=1;ts,cid=t.open_(c,k,salt,duration=10);w=t.accept(c,k,ts,cid,salt+1000)
            for _ in range(11):t.rpc('block/create',{})
            out=X(L+'::claim_'+t.route(k),[w,f'{salt}field'])
            t.spend_payout(k,600)
            t.check(f'{c}/{k} default owner',f'owner: {t.DEV}' in out[-2])
            X(L+'::claim_'+t.route(k),[w,f'{salt}field'],fail=True)
            X(P+'::cancel_'+t.route(c),[cid,ts,f'{salt}field','600u128'])
            t.check(f'{c}/{k} default clears collateral',t.mapping(L,'liabilities',f"'{t.ASSETS[k][0]}'")=='0u128')
    # At maturity either side may finalize, but exactly one terminal path wins.
    ts,cid=t.open_('sol','usad',1190,duration=10);w=t.accept('sol','usad',ts,cid,2190)
    for _ in range(11):t.rpc('block/create',{})
    t.repay('sol','usad',w,2190)
    X(L+'::claim_compliant',[w,'1190field'],fail=True)
    X(P+'::withdraw_arc20',[cid,ts,'1190field','440u128']);X(P+'::cancel_arc20',[cid,ts,'1190field','600u128'])
    t.check('late repayment wins atomically over a later claim','status: 2u8' in t.mapping(L,'loans',t.lid(w)))
    # Invalid compliance proof fails without spending the original record, for both tokens.
    for i,k in enumerate(['usdcx','usad']):
        salt=1200+i;ts=t.terms(k,'aleo',salt);r=t.private(k,1000)
        args=['1field',ts,r,'1000u128',f'{salt}field']
        X(P+'::open_compliant',args+[t.PROOFS.replace('1u32','0u32')],fail=True)
        cid=X(P+'::open_compliant',args+[t.PROOFS])[-2]
        X(P+'::cancel_compliant',[cid,ts,f'{salt}field','1000u128'])
        t.check(k+' invalid proof preserves deposit',t.mapping(P,'closed',cid)=='true')
    # Deficit isolates one token, and blocks the FIRST collateral claimant.
    ts,cid=t.open_('sol','usad',1300)
    w1=t.accept('sol','usad',ts,cid,2300,nonce=1);w2=t.accept('sol','usad',ts,cid,2301,nonce=2)
    X('usad_stablecoin.aleo::burn_public',[L,'600u128'])
    t.repay('sol','usad',w1,2300,True)
    t.check('burn preserves both loans and total liabilities',t.mapping(L,'liabilities',"'usad_stablecoin'")=='1200u128' and all('status: 1u8' in t.mapping(L,'loans',t.lid(w)) for w in [w1,w2]))
    other,oc=t.open_('wbtc','aleo',1301);ow=t.accept('wbtc','aleo',other,oc,2302)
    t.repay('wbtc','aleo',ow,2302);X(P+'::cancel_arc20',[oc,other,'1301field','600u128']);X(P+'::withdraw_arc20',[oc,other,'1301field','440u128'])
    t.check('unrelated asset remains usable during deficit',t.mapping(P,'liabilities',"'arc20_wbtc'")=='0u128')
    X('usad_stablecoin.aleo::mint_public',[L,'600u128'])
    X('usad_stablecoin.aleo::set_pause_status',['true']);t.repay('sol','usad',w1,2300,True)
    X('usad_stablecoin.aleo::set_pause_status',['false']);t.repay('sol','usad',w1,2300);t.repay('sol','usad',w2,2301)
    X(P+'::withdraw_arc20',[cid,ts,'1300field','880u128']);X(P+'::cancel_arc20',[cid,ts,'1300field','200u128'])
    # A deficit in the credit reserve must not reject an incoming repayment.
    # The deficit remains visible and still blocks outgoing lender withdrawals.
    ts,cid=t.open_('sol','usad',1310);w=t.accept('sol','usad',ts,cid,2310)
    X('arc20_sol.aleo::burn_public',[P,'300u128'])
    t.repay('sol','usad',w,2310)
    X(P+'::withdraw_arc20',[cid,ts,'1310field','440u128'],fail=True)
    t.check('credit deficit cannot strand borrower collateral','status: 2u8' in t.mapping(L,'loans',t.lid(w)))
    X('arc20_sol.aleo::mint_public',[P,'300u128'])
    X(P+'::withdraw_arc20',[cid,ts,'1310field','440u128']);X(P+'::cancel_arc20',[cid,ts,'1310field','600u128'])
    # Large u128 ARC-20 principal; native narrowing must reject, not truncate.
    n=2**80;salt=1400;ts=t.terms('sol','wbtc',salt).replace('100u128',f'{n}u128').replace('600u128',f'{n}u128').replace('15000u64','10000u64').replace('11000u64','10000u64')
    cid=X(P+'::open_arc20',['1field',ts,t.private('sol',n),f'{n}u128',f'{salt}field'])[-2]
    w=X(L+'::accept_arc20_arc20',['1field',cid,ts,f'{n}u128',t.private('wbtc',n,B,BK),'2400field'],BK)[-2]
    X(L+'::repay_arc20_arc20',[w,t.private('sol',n,B,BK),f'{n}u128','2400field'],BK)
    X(P+'::withdraw_arc20',[cid,ts,'1400field',f'{n}u128']);X(P+'::cancel_arc20',[cid,ts,'1400field','0u128'])
    t.check('amount above u64 survives full loan cycle',t.mapping(P,'liabilities',"'arc20_sol'")=='0u128')
    ts=t.terms('aleo','sol',1401)
    X(P+'::open_aleo',['1field',ts,t.private('aleo',1000),f'{2**64}u128','1401field'],fail=True)
    # Wrong schema version / token_id cannot bypass admission.
    ts=t.terms('sol','wbtc',1402)
    for bad in [ts.replace('version: 1u16','version: 2u16'),ts.replace('token_id: 0field','token_id: 1field')]:
        X(P+'::open_arc20',['1field',bad,t.private('sol',1000),'1000u128','1402field'],fail=True)

    # Unknown token is admitted by a transaction; no core code/deployment changes.
    import hashlib
    from pathlib import Path
    paths=[t.ENTRY.parent/n/'src/main.leo' for n in ['pwn_proposal_poc','pwn_loan_poc']]
    hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    desc="{ program_id: 'pwn_delta_token', token_id: 0field, family: 2u8, version: 1u16 }"
    ts=t.terms('sol','aleo',1500).replace(t.asset('sol'),desc)
    record=X('pwn_delta_token.aleo::mint',[t.DEV,'1000u128'])[0]
    args=['1field',ts,record,'1000u128','1500field']
    X(P+'::open_arc20',args,fail=True)
    X(H+'::set_asset',["'pwn_delta_token'",'2u8','true'])
    X('pwn_delta_token.aleo::set_bad',['true'])
    X(P+'::open_arc20',args,fail=True)
    t.check('inexact deposit rolls back token reserve',t.mapping('pwn_delta_token.aleo','balances',P) in [None,'0u128'])
    X('pwn_delta_token.aleo::set_bad',['false'])
    cid=X(P+'::open_arc20',args)[-2]
    X(P+'::cancel_arc20',[cid,ts,'1500field','1000u128'])
    t.check('new token works with unchanged core',hashes==[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
    # Arithmetic edge cases against Python's unbounded integer oracle.
    import json
    for i,(n,r) in enumerate([(2**120,10000),(2**100+123,15001),(1,1),(2**128-1,10000)]):
        out=t.OUT/'math.json'
        code,log=t.cli(['run','math_round',f'{n}u128',f'{r}u64','--path',t.ENTRY,'--json-output='+str(out)],f'math-round-{i}')
        t.check(f'wide rounded multiplication {i}',code==0 and json.loads(out.read_text())['outputs'][0]==f'{(n*r+9999)//10000}u128')
    n=2**100+987;apr=1000000000;elapsed=1000000;out=t.OUT/'math.json'
    code,log=t.cli(['run','math_interest',f'{n}u128',f'{apr}u32',f'{elapsed}u32','--path',t.ENTRY,'--json-output='+str(out)],'math-interest')
    t.check('wide accrued interest avoids intermediate overflow',code==0 and json.loads(out.read_text())['outputs'][0]==f'{n*apr*elapsed//315360000000}u128')

    # Freezing escrow rejects atomically; restoring the issuer state permits settlement.
    ts,cid=t.open_('wbtc','usdcx',1600);w=t.accept('wbtc','usdcx',ts,cid,2600)
    f='usdcx_freezelist.aleo';old=t.mapping(f,'freeze_list_root','1u8');out=t.OUT/'freeze-root.json'
    code,log=t.cli(['run','freeze_root',L,'--path',t.ENTRY,'--json-output='+str(out)],'freeze-root')
    assert code==0,log[-2000:]
    root=json.loads(out.read_text())['outputs'][0]
    X(f+'::update_freeze_list',[L,'true','1u32',old,root]);t.repay('wbtc','usdcx',w,2600,True)
    X(f+'::update_freeze_list',[L,'false','1u32',root,old]);t.repay('wbtc','usdcx',w,2600)
    t.spend_payout('usdcx',600,BK,B)
    X(P+'::withdraw_arc20',[cid,ts,'1600field','440u128']);X(P+'::cancel_arc20',[cid,ts,'1600field','600u128'])
    t.check('freeze recovery retains correct accounting',t.mapping(L,'liabilities',"'usdcx_stablecoin'")=='0u128')
    # Authorized, delayed additive upgrade preserves and settles a live position.
    ts,cid=t.open_('sol','usad',1700);w=t.accept('sol','usad',ts,cid,2700)
    for name in ['pwn_config_poc','pwn_hub_poc','pwn_proposal_poc','pwn_loan_poc']:
        p=t.ENTRY.parent/name/'src/main.leo';s=p.read_text();p.write_text(s.replace('    @custom','    fn release_version() -> u8 { return 2u8; }\n    @custom'))
    common=list(t.COMMON);common[1]=t.ENTRY.parent/'pwn_loan_poc'
    # Names shorter than 10 characters carry a 10^(10-len) credit deployment premium; the account also pays for the rejected attempts.
    X('credits.aleo::transfer_public',[B,'5000000000u64'])
    code,log=t.cli(['upgrade',*common,'--skip','credits.aleo','--private-key',BK,'--skip-deploy-certificate','--broadcast','--yes'],'upgrade-denied')
    t.check('unauthorized upgrade rejected',log.count('Transaction rejected.')==4 and 'confirmed!' not in log.lower())
    for name in ['pwn_config_poc','pwn_hub_poc','pwn_proposal_poc','pwn_loan_poc']:
        X(C+'::schedule_upgrade',[name+'.aleo','1u16'])
    code,log=t.cli(['upgrade',*common,'--skip','credits.aleo','--private-key',t.AK,'--skip-deploy-certificate','--broadcast','--yes'],'upgrade-too-early')
    t.check('scheduled upgrade rejected before timelock',log.count('Transaction rejected.')==4 and 'confirmed!' not in log.lower())
    for _ in range(721):t.rpc('block/create',{})
    code,log=t.cli(['upgrade',*common,'--skip','credits.aleo','--private-key',t.AK,'--skip-deploy-certificate','--broadcast','--yes'],'upgrade-authorized')
    assert code==0,log[-3000:]
    t.check('authorized upgrade code callable',X(L+'::release_version')[0]=='2u8')
    t.repay('sol','usad',w,2700)
    X(P+'::withdraw_arc20',[cid,ts,'1700field','440u128']);X(P+'::cancel_arc20',[cid,ts,'1700field','600u128'])
    t.check('pre-upgrade loan settles after upgrade','status: 2u8' in t.mapping(L,'loans',t.lid(w)))
