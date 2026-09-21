#!/usr/bin/env python3
"""Stage the protocol programs and pinned mainnet token code on a disposable local test network."""
import hashlib,json,re,shutil
from pathlib import Path
from generate_multitoken import ROOT,BOOT,MATH
DEV='aleo1rhgdu77hgyqd3xjj8ucu3jj9r2krwz6mnzyd80gncr5fxcwlh5rsvzp9px'
CORE=['pwn_config_poc','pwn_hub_poc','pwn_proposal_poc','pwn_loan_poc']
TOKENS=['merkle_tree','arc20_multisig_core','arc20_sol','arc20_wbtc','usdcx_multisig_core','usdcx_freezelist','usdcx_stablecoin','usad_multisig_core','usad_freezelist','usad_stablecoin']

def stage():
    base=ROOT/'artifacts/multitoken/local-workspace'; vendor=base/'vendor';vendor.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'vendor/credits.network.aleo',vendor/'credits.aleo')
    provenance=[]
    for name in TOKENS:
        src=ROOT/'research'/('merkle_tree.aleo' if name=='merkle_tree' else 'multitoken/'+name+'.aleo')
        original=src.read_text();s=original
        # Only initialize/deployment bootstrap assertions; preserve operational restrictions.
        for block in re.findall(r'(?:finalize initialize:|constructor:).*?(?=\n\n|\Z)',s,re.S):
            changed=re.sub(r'(assert\.eq (?:r\d+|program_owner) )aleo1[a-z0-9]+;',r'\g<1>'+DEV+';',block)
            changed=re.sub(r'(set 8u16 into address_to_role\[)aleo1[a-z0-9]+',r'\g<1>'+DEV,changed)
            s=s.replace(block,changed)
        if 'constructor:' not in s:s+='\nconstructor:\n    assert.eq edition 0u16;\n'
        (vendor/(name+'.aleo')).write_text(s)
        provenance.append(dict(source=str(src.relative_to(ROOT)),sha256=hashlib.sha256(original.encode()).hexdigest(),fixture_sha256=hashlib.sha256(s.encode()).hexdigest(),changed_lines=[dict(before=a,after=b) for a,b in zip(original.splitlines(),s.splitlines()) if a!=b],appended_constructor='constructor:' not in original))
    (base/'fixture-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    for name in CORE:
        src=ROOT/name; dst=base/name;(dst/'src').mkdir(parents=True,exist_ok=True)
        (dst/'src/main.leo').write_text((src/'src/main.leo').read_text().replace(BOOT,DEV))
        m=json.loads((src/'program.json').read_text())
        for d in m['dependencies']:
            d['path']='../vendor/credits.aleo' if d['name']=='credits.aleo' else '../'+d['name'][:-5]
        (dst/'program.json').write_text(json.dumps(m,indent=2)+'\n')
    # Deliberately non-conforming transfer semantics to test reserve postconditions.
    bad=base/'pwn_delta_token';(bad/'src').mkdir(parents=True,exist_ok=True)
    (bad/'program.json').write_text(json.dumps(dict(program='pwn_delta_token.aleo',version='0.1.0',description='TEST ONLY: inexact transfers',license='MIT',leo='4.4.2',dependencies=[])))
    (bad/'src/main.leo').write_text("""
program pwn_delta_token.aleo {
    record Token { owner: address, amount: u128 }
    mapping balances: address => u128;
    mapping bad: bool => bool;
    fn set_bad(public value: bool) -> Final { return final { bad.set(true, value); }; }
    fn mint(recipient: address, amount: u128) -> Token { return Token { owner: recipient, amount: amount }; }
    fn transfer_private_to_public(input: Token, public recipient: address, public amount: u128) -> (Token, Final) {
        let change = Token { owner: input.owner, amount: input.amount - amount };
        return (change, final {
            let received = bad.get_or_use(true, false) ? amount - 1u128 : amount;
            balances.set(recipient, balances.get_or_use(recipient, 0u128) + received);
        });
    }
    fn transfer_public_to_private(recipient: address, public amount: u128) -> (Token, Final) {
        let output = Token { owner: recipient, amount: amount }; let caller = std::ctx::caller();
        return (output, final { balances.set(caller, balances.get(caller) - amount); });
    }
    @noupgrade constructor() {}
}
""")
    # Driver imports are fixture-only. Protocol packages have no token-specific imports.
    driver=base/'pwn_local_fixture';(driver/'src').mkdir(parents=True,exist_ok=True)
    deps=[dict(name=n+'.aleo',location='local',path='../vendor/'+n+'.aleo',edition=None) for n in TOKENS]
    deps += [dict(name='pwn_delta_token.aleo',location='local',path='../pwn_delta_token',edition=None)]
    deps += [dict(name='credits.aleo',location='local',path='../vendor/credits.aleo',edition=None)]
    deps += [dict(name=n+'.aleo',location='local',path='../'+n,edition=None) for n in CORE]
    (driver/'program.json').write_text(json.dumps(dict(program='pwn_local_fixture.aleo',version='0.1.0',description='Local-only fixture loader',license='MIT',leo='4.4.2',dependencies=deps),indent=2)+'\n')
    (driver/'src/main.leo').write_text('\n'.join('import '+d['name']+';' for d in deps)+MATH+'''
struct Authority { domain: u8, protocol: address, account: address, salt: field }
program pwn_local_fixture.aleo {
    fn auth(account: address, salt: field) -> field {
        return BHP256::hash_to_field(Authority { domain: 1u8, protocol: pwn_proposal_poc.aleo, account: account, salt: salt });
    }
    fn freeze_root(account: address) -> field { return Poseidon4::hash_to_field([1field, 0field, account as field]); }
    fn math_round(amount: u128, ratio: u64) -> u128 { return rounded(amount, ratio); }
    fn math_interest(amount: u128, apr: u32, elapsed: u32) -> u128 { return accrued(amount, apr, elapsed); }
    fn dynamic_sol(input: arc20_sol.aleo::Token) -> dyn record { return input as dyn record; }
    fn forward_set_asset(public token: identifier, public family: u8, public enabled: bool) -> Final {
        let action = pwn_hub_poc.aleo::set_asset(token, family, enabled);
        return final { action.run(); };
    }
    fn forward_set_admin(public admin: address, public upgrader: address) -> Final {
        let action = pwn_config_poc.aleo::set_admin(admin, upgrader);
        return final { action.run(); };
    }
    @noupgrade constructor() {}
}
''')
    return base
if __name__=='__main__':print(stage())
