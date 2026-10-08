from pathlib import Path
from copy import deepcopy
from lxml import html

D=Path(__file__).resolve().parent.parent
root=html.fromstring((D/'private-lending-aleo-grant-overview-v5.html').read_text())
original=html.fromstring((D/'private-lending-aleo-grant-overview-v3.html').read_text())

def replace(old,new):
    found=0
    for e in root.iter():
        if not isinstance(e.tag,str):continue
        for attr in ('text','tail'):
            value=getattr(e,attr)
            if value and old in value:
                setattr(e,attr,value.replace(old,new));found+=1
    assert found,old

replace(' · September 2026','')
replace('13 EVM mainnets','13 EVM chains')
replace('its pivot towards longer-term crypto-backed loans and mortgages.', 'building on PWN’s original ambition to make crypto-backed mortgages possible.')
replace('Founder of OWN (onchain mortgages) and PWN DAO.', 'Founder of PWN DAO and OWN.')
replace('Engineer with four years of experience building PWN’s DeFi lending application as a contractor.', 'Engineer, 4 years of building PWN’s DeFi lending application.')
replace('If the borrower repays, collateral is returned. After maturity, the lender can claim it if the loan remains unpaid; repayment is still possible until a default claim settles.', 'If the borrower repays before maturity, collateral is returned. If there is no repayment at maturity, the lender can claim the collateral.')

# Restore the two original lifecycle captions, including emphasis.
oldsvg=original.xpath('//section[h2="Protocol model"]//svg')[0]
newsvg=root.xpath('//section[h2="Protocol model"]//svg')[0]
for y in ('38','126'):
    old=oldsvg.xpath(f'.//text[@x="330"][@y="{y}"]')[0]
    new=newsvg.xpath(f'.//text[@x="330"][@y="{y}"]')[0]
    new.getparent().replace(new,deepcopy(old))

replace('Multiple draws reuse one funded offer, but do not hide its lender: each PoC loan publicly references the commitment. Direct offers use the same mechanism with a restricted acceptor; we will prefer a private authorisation check over publishing the acceptor’s address.', 'Multiple draws reuse one funded offer. The lender’s address stays private in the lending calls, while each loan publicly references the commitment it draws from. Direct offers use the same mechanism, with acceptance restricted to a designated borrower through a private proof of authorisation.')
replace(' New repayment or default rules must be supported by the product interface agreed before the core becomes immutable. Milestone 1 will define and validate these interfaces; the current PoC still binds a specific Proposal and Loan pair.', '')

# Restore the original privacy section, with the requested deletion and short addition.
oldsec=original.xpath('//section[h2="Privacy model, measured on testnet"]')[0]
newsec=root.xpath('//section[h2="Privacy model, measured on testnet"]')[0]
privacy=deepcopy(oldsec);privacy.set('class','privacy-section')
newsec.getparent().replace(newsec,privacy)
chip=privacy.xpath('.//span[text()="specific terms of an individual loan"]')[0]
chip.getparent().remove(chip)
# Preserve the original categories while avoiding claims that public activity is hidden.
chip=privacy.xpath('.//span[text()="repayment history"]')[0]
chip.text='repayment history linked to a wallet identity'
small=privacy.xpath('.//div[h4="Private in V1"]/p')[0]
small.text='Identities are not written to protocol public state; loan activity remains visible under public identifiers.'
cell=privacy.xpath('.//tr[td/strong="Commitment → loan link"]/td[3]')[0]
cell.text='The link is public; it does not by itself reveal the lender’s address'
p=html.Element('p');p.text='Direct offers can keep more terms private.'
fig=privacy.xpath('./div[contains(@class,"fig")]')[0];fig.addprevious(p)
replace(' (September 2026)','')

# Remove every launch-cap commitment consistently; the audit precedes mainnet deployment.
cap=root.xpath('//div[contains(@class,"callout")][p/span="Capped launch."]')[0]
cap.getparent().remove(cap)
replace('capped mainnet launch','mainnet launch')
replace('a reviewed, mainnet launch','a reviewed mainnet launch')
replace('Capped mainnet','Mainnet')
replace('direct offers, launch caps,','direct offers,')
replace('multisig authority, launch caps, and','multisig authority, and')
replace('protocol-level launch caps and emergency stop in Config','an emergency stop in Config')
replace('non-upgradeable mainnet deployment with caps','non-upgradeable mainnet deployment')
root.xpath('//section[div/div/h2="Out of scope"]')[0].set('class','keep')

output=html.tostring(root,encoding='unicode',method='html',doctype='<!DOCTYPE html>').replace('grant-assets-v5/','grant-assets-v6/')
assert 'September 2026' not in output
assert 'capped' not in output.lower() and 'launch caps' not in output
(D/'private-lending-aleo-grant-overview-v6.html').write_text(output)

# Reuse the verified authoring pipeline without changing earlier versions.
for src,dst in [('render_illustrated_grant.cjs','render_illustrated_grant_v6.cjs'),('build_illustrated_grant.py','build_illustrated_grant_v6.py')]:
    text=(D/'research-2026-10-07'/src).read_text().replace('-v5','-v6')
    if src.endswith('.py'):
        text=text.replace('self.paragraph(label,size=9.5,color=MUTED,bold=True)','self.paragraph(label,size=9.5,color=MUTED,bold=True).paragraph_format.keep_with_next=True')
        text=text.replace("self.paragraph(c,size=9.5,bold=c.get('class')=='n')", "self.paragraph(c,size=9.5,bold=c.get('class')=='n').paragraph_format.keep_with_next=True")
    (D/'research-2026-10-07'/dst).write_text(text)
assets=D/'grant-assets-v6';assets.mkdir(exist_ok=True)
for font in (D/'grant-assets-v5').glob('*.ttf'):(assets/font.name).write_bytes(font.read_bytes())
print(D/'private-lending-aleo-grant-overview-v6.html')
