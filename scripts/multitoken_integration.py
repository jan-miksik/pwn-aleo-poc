#!/usr/bin/env python3
"""Local lifecycle tests against pinned real token bytecode. No live broadcast."""
import argparse,json,re,socket,subprocess,time,urllib.request,sys
from multitoken_workspace import ROOT,stage,DEV
from multitoken_test_support import accepted, rejection_reason, private_payout_matches
# Published Leo development keys: local devnode only, never a public network.
AK='APrivateKey1zkp8CZNn3yeCseEtxuVPbDCwSyhGW6yZKUYKfgXmcpoGPWH'
BK='APrivateKey1zkpGPDbTcP2rWRMFLa1quxwGMK2BNJ16HWjYjofTH1pMUYj'
B='aleo16k6wjpe5snzfhzf07mfze8j8lyg6vgyfe25vu67ykpvu6mv6ng8q8p78ue'
_proof='{ siblings: ['+', '.join(['0field']*16)+'], leaf_index: 1u32 }'
PROOFS='['+_proof+', '+_proof+']'
OUT=None  # Initialized by main; importing helpers must not create artifacts.
LEO=str(ROOT/'scripts/leo');C='pwn_config_poc.aleo';H='pwn_hub_poc.aleo';P='pwn_proposal_poc.aleo';L='pwn_loan_poc.aleo'
ASSETS={'aleo':('credits',1),'sol':('arc20_sol',2),'wbtc':('arc20_wbtc',2),'usdcx':('usdcx_stablecoin',3),'usad':('usad_stablecoin',3)}
FAMILY={1:'aleo',2:'arc20',3:'compliant'}
seq=0;checks=[]
def check(name,ok):
    assert ok,name
    checks.append({'test':name,'status':'PASS'});print('PASS',name,flush=True)
def cli(args,label):
    pth=OUT/(label+'.log')
    with pth.open('w') as f:p=subprocess.run([LEO,*map(str,args)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    log=re.sub(r'\x1b\[[0-9;]*m','',pth.read_text());pth.write_text(log)
    return p.returncode,log

def rpc(path,body=None):
    req=urllib.request.Request(ENDPOINT+'/testnet/'+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
def height():return rpc('block/height/latest')
def mapping(prog,name,key):return rpc(f'program/{prog}/mapping/{name}/{key}')
PROVED=[]
def execute(fn,args=(),key=AK,fail=False,prove=False):
    """prove=True generates a real execution proof (record inclusion, program binding); the node still skips proof verification and consensus."""
    global seq,LAST
    seq+=1;label=f'{seq:04d}-'+fn.replace('::','-');path=OUT/(label+'.json');path.unlink(missing_ok=True)
    code,log=cli(['execute',fn,*args,*COMMON,'--private-key',key,*([] if prove else ['--skip-execute-proof']),'--broadcast','--yes','--json-output='+str(path)],label)
    result=json.loads(path.read_text()) if path.exists() else {}
    ok=accepted(code,result,log)
    if prove:PROVED.append(dict(label=label,accepted=ok,error=None if ok else re.sub(r'\s+',' ',log[-1500:]).strip()[-400:]))
    if fail:
        reason=rejection_reason(code,result,log,(OUT/'devnode.log').read_text())
        assert reason is not None,label+' expected protocol rejection, got:\n'+log[-3500:]
        if prove:assert reason=='record commitment absent from ledger',label+' did not reach the record-inclusion check'
        check(label+' rejected: '+reason,True)
    else:assert ok,label+'\n'+log[-3500:]
    LAST=result
    return result.get('outputs',[])
def decrypt_payout(k,amount,key=AK,owner=DEV):
    """Read the actual nested output; a dyn record only exposes its root."""
    tx=rpc('transaction/'+LAST['transaction_id'])
    prog=ASSETS[k][0]+'.aleo'
    transitions=[x for x in tx['execution']['transitions'] if x['program']==prog and x['function']=='transfer_public_to_private']
    assert len(transitions)==1,transitions
    records=[x['value'] for x in transitions[0]['outputs'] if x.get('value','').startswith('record1')]
    record=records[1 if ASSETS[k][1]==3 else 0]
    code,plain=cli(['account','decrypt','-k',key,'-c',record],f'decrypt-{seq}')
    assert code==0,plain
    check(k+' payout decrypts with correct owner and amount',private_payout_matches(plain,owner,amount,64 if k=='aleo' else 128))
    return plain[plain.index('{'):plain.rindex('}')+1]

def spend_payout(k,amount,key=AK,owner=DEV):
    """Decrypt the actual nested token output, then spend it in another transaction."""
    plain=decrypt_payout(k,amount,key,owner)
    prog=ASSETS[k][0]+'.aleo'
    args=[owner,'1u128',plain,PROOFS] if ASSETS[k][1]==3 else [plain,owner,'1u64' if k=='aleo' else '1u128']
    execute(prog+'::transfer_private_to_public',args,key)
    check(k+' payout can actually be spent',True)

def asset(k):
    p,f=ASSETS[k];return f"{{ program_id: '{p}', token_id: 0field, family: {f}u8, version: 1u16 }}"
def route(k):return FAMILY[ASSETS[k][1]]
def proofs(k):return [PROOFS] if ASSETS[k][1]==3 else []
def private(k,amount,account=DEV,key=AK):
    if k=='aleo':return execute('credits.aleo::transfer_public_to_private',[account,f'{amount}u64'],key)[0]
    p,f=ASSETS[k];out=execute(p+'.aleo::mint_private',[account,f'{amount}u128'])
    return out[1 if f==3 else 0]
def auth(salt):
    path=OUT/'auth.json';code,log=cli(['run','auth',DEV,f'{salt}field','--path',ENTRY,'--json-output='+str(path)],'auth')
    assert code==0,log[-2000:]
    return json.loads(path.read_text())['outputs'][0]
def terms(c,k,salt,duration=1000,apr=0):
    return f'{{ credit_asset: {asset(c)}, collateral_asset: {asset(k)}, min_draw: 100u128, max_draw: 600u128, collateral_ratio: 15000u64, repayment_ratio: 11000u64, accruing_apr: {apr}u32, duration: {duration}u32, expiry: {height()+5000}u32, lender_auth: {auth(salt)} }}'
def open_(c,k,salt,duration=1000):
    ts=terms(c,k,salt,duration);out=execute(P+'::open_'+route(c),['1field',ts,private(c,1000),'1000u128',f'{salt}field']+proofs(c));return ts,out[-2]
def accept(c,k,ts,cid,salt,nonce=1):
    out=execute(L+'::accept_'+route(c)+'_'+route(k),[f'{nonce}field',cid,ts,'400u128',private(k,1000,B,BK),f'{salt}field']+proofs(k),BK)
    check(f'{c}/{k} private credit owner',f'owner: {B}' in out[-4])
    return out[-2]
def repay(c,k,w,salt,fail=False,prove=False):return execute(L+'::repay_'+route(c)+'_'+route(k),[w,private(c,500,B,BK),'440u128',f'{salt}field']+proofs(c),BK,fail,prove)
def lid(w):return re.search(r'loan_id:\s*(\d+field)',w).group(1)
def main(argv=None):
    global ENTRY,COMMON,ENDPOINT,OUT,seq,LAST
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--security-only',action='store_true')
    modes.add_argument('--invariants-only',action='store_true')
    parser.add_argument('--seed',type=int,default=20260920)
    parser.add_argument('--steps',type=int,default=30,help='Random actions after the invariant regression prefix')
    options=parser.parse_args(argv)
    if options.steps<0:parser.error('--steps must be nonnegative')
    mode='security' if options.security_only else 'invariants' if options.invariants_only else 'integration'
    OUT=ROOT/'artifacts/multitoken'/mode
    OUT.mkdir(parents=True,exist_ok=True)
    seq=0;LAST={};checks.clear();PROVED.clear()
    base=stage();ENTRY=base/'pwn_local_fixture'
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    ENDPOINT=f'http://127.0.0.1:{port}'
    COMMON=['--path',ENTRY,'--endpoint',ENDPOINT,'--network','testnet','--devnet','--consensus-version','19','--offline']
    stream=(OUT/'devnode.log').open('w');node=subprocess.Popen([LEO,'devnode','start','--private-key',AK,'--socket-addr',f'127.0.0.1:{port}','-v','0'],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
    completed=False
    try:
        for _ in range(100):
            assert node.poll() is None,'devnode exited'
            try:height();time.sleep(1);break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('devnode not ready')
        code,log=cli(['deploy',*COMMON,'--skip','credits.aleo','--private-key',AK,'--skip-deploy-certificate','--broadcast','--yes'],'deploy')
        assert code==0,log[-4000:]
        check('protocol and real token fixtures deployed',log.count('Deployment confirmed!')==16)
        execute(C+'::initialize');execute(H+'::set_tag',[P,'2u8','true']);execute(H+'::set_tag',[L,'1u8','true'])
        execute('credits.aleo::transfer_public',[B,'1000000000u64'])
        for k,(p,f) in ASSETS.items():
            execute(H+'::set_asset',[f"'{p}'",f'{f}u8','true'])
            if f==3:
                execute(p+'.aleo::initialize',['1u128','1u128','6u8','1000000000000000000000000000000u128',DEV])
                execute(p.replace('stablecoin','freezelist')+'.aleo::initialize',[DEV,'1000u32'])
                execute(p.replace('stablecoin','freezelist')+'.aleo::update_role',[DEV,'24u16'])
            if f!=1:execute(p+'.aleo::update_role',[DEV,'15u16'])
        salt=100
        for c in ([] if options.security_only or options.invariants_only else ASSETS):
            for k in ASSETS:
                salt+=1;ts,cid=open_(c,k,salt);w=accept(c,k,ts,cid,salt+1000)
                check(f'{c}/{k} locked',mapping(P,'available_credit',cid)=='600u128' and 'status: 1u8' in mapping(L,'loans',lid(w)))
                out=repay(c,k,w,salt+1000)
                check(f'{c}/{k} returned collateral',f'owner: {B}' in out[-2])
                execute(P+'::withdraw_'+route(c),[cid,ts,f'{salt}field','440u128'])
                execute(P+'::cancel_'+route(c),[cid,ts,f'{salt}field','600u128'])
                check(f'{c}/{k} cleared',mapping(P,'liabilities',f"'{ASSETS[c][0]}'")=='0u128' and mapping(L,'liabilities',f"'{ASSETS[k][0]}'")=='0u128')
        if options.security_only:
            import multitoken_security
            multitoken_security.run(sys.modules[__name__])
        if options.invariants_only:
            import multitoken_invariants
            multitoken_invariants.run(sys.modules[__name__],options.seed,options.steps)
        completed=True
    finally:
        node.terminate()
        try:node.wait(timeout=10)
        except subprocess.TimeoutExpired:node.kill();node.wait()
        stream.close()
        (OUT/'results.json').write_text(json.dumps(dict(completed=completed,mode=mode,seed=options.seed,steps=options.steps,checks=checks,attempted_transactions=seq,execution_proofs=False,proved_transactions=PROVED,deployment_certificates=False,consensus=False,node_verifies_proofs=False),indent=2)+'\n')
    print(f'{len(checks)} checks passed',flush=True)
if __name__=='__main__':main()
