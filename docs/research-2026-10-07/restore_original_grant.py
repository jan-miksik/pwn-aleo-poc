"""Apply narrow content edits to the pre-edit illustrated HTML grant source."""
from pathlib import Path
from lxml import html, etree
import hashlib
import json

DOCS=Path(__file__).resolve().parent.parent
SOURCE=DOCS/'private-lending-aleo-grant-overview-v3.html'
OUT=DOCS/'private-lending-aleo-grant-overview-v5.html'

def content(node, fragment):
    for child in list(node): node.remove(child)
    node.text=None
    for x in html.fragments_fromstring(fragment):
        if isinstance(x,str): node.text=(node.text or '')+x
        else: node.append(x)

def paragraph_after(node, fragment, cls=None):
    p=html.Element('p')
    if cls: p.set('class',cls)
    content(p,fragment);node.addnext(p);return p

def section(root, heading):
    return root.xpath('//section[h2[text()=$t]]',t=heading)[0]

def main():
    root=html.fromstring(SOURCE.read_text())
    body=root.find('body')
    root.xpath('//div[@class="masthead"]/div[@class="sub"]')[0].text='Universal lending infrastructure for Aleo, built in Leo by the team behind OWN and inspired by PWN’s bilateral, oracle-free lending mechanics.'
    root.xpath('//div[@class="facts keep"]/div[@class="fact"][1]//small')[0].text='Team behind OWN · PWN protocol lineage'
    leads=root.xpath('//body/p[@class="lead"]')
    content(leads[0], 'The applicant is the <strong>PWN DAO Foundation</strong>. The team previously developed PWN, a peer-to-peer lending protocol deployed on 13 EVM mainnets, and now focuses on <a href="https://ownlabs.co/">OWN</a>, its pivot towards longer-term crypto-backed loans and mortgages. PWN’s contracts remain publicly available lending infrastructure. Lenders and borrowers agree on fixed loan terms directly, without price oracles or price-based liquidations. This bilateral model fits a privacy-first ZK chain particularly well, because individual loans stay isolated instead of depending on global liquidity, utilisation and liquidation state.')
    content(leads[1], 'This grant funds <strong>universal lending infrastructure for Aleo</strong>, designed around PWN v1.5’s lending mechanics: funded Elastic Proposals as the first offer type, private bilateral lending, a modular Hub and Config layer, a TypeScript SDK and a reference application, <strong>with a capped mainnet launch as the final milestone.</strong> A feasibility PoC of the core programs is already deployed and exercised on the Aleo testnet (see <em>Current status</em>).')
    team=html.fromstring('''<section class="team-section"><h2>Team</h2>
    <p><strong>Josef Jelacic</strong> — Founder of OWN (onchain mortgages) and PWN DAO. <a href="https://www.linkedin.com/in/josefje/">LinkedIn</a></p>
    <p><strong>Šimon Kozák</strong> — Engineer, Founding Engineer &amp; CTO at PWN DAO and OWN. <a href="https://www.linkedin.com/in/simon-kozak/">LinkedIn</a> · <a href="https://github.com/microHoffman">GitHub</a></p>
    <p><strong>Jan Mikšík</strong> — Engineer with four years of experience building PWN’s DeFi lending application as a contractor. <a href="https://www.linkedin.com/in/jan-miksik/">LinkedIn</a> · <a href="https://github.com/jan-miksik">GitHub</a></p></section>''')
    leads[1].addnext(team)
    # Keep the original first-page protocol panel intact; give the added team room.
    protocol=section(root,'Protocol model')
    protocol.set('class','page-break')
    following=protocol.getnext()
    if following is not None and following.get('class')=='page-break':
        following.getparent().remove(following)
    section(root,'Feasibility questions, answered by the PoC').set('class','page-break')
    p=protocol.find('p')
    content(p, 'Each loan fixes the credit asset and amount, the collateral asset and amount, the repayment amount and the maturity. If the borrower repays, collateral is returned. After maturity, the lender can claim it if the loan remains unpaid; repayment is still possible until a default claim settles. There is no price feed, no health factor and no price-based liquidation, which makes the model a natural fit for minimising public disclosure on Aleo.')
    svg=protocol.xpath('.//svg')[0]
    for t in svg.xpath('.//text'):
        text=''.join(t.itertext()).strip()
        if text.startswith('borrower repays'):
            content(t,'borrower repays before a default claim')
        elif text.startswith('no repayment'):
            content(t,'loan unpaid after maturity')
    elastic=section(root,'Elastic Proposal: the default offer type')
    paragraph_after(elastic.find('p'), '<strong>Proposal versus loan.</strong> A proposal is an offer and its available funding; each accepted draw creates a separate loan with its own collateral, repayment obligation and maturity. Proposal expiry stops new draws, not existing loans. Cancelling a proposal returns unused funding without cancelling active loans.')
    p=elastic.xpath('./h3/following-sibling::p')[0]
    content(p, 'An Aleo transaction has a single signer and a program cannot spend a private record on a counterparty’s behalf, so our asynchronous acceptance flow commits capital in advance. Elastic proposals make every offer backed by real capital and allow discovery from public state without a proprietary backend. Multiple draws reuse one funded offer, but do not hide its lender: each PoC loan publicly references the commitment. Direct offers use the same mechanism with a restricted acceptor; we will prefer a private authorisation check over publishing the acceptor’s address.')
    arch=section(root,'Architecture')
    # Retain the original diagram and table; annotate them as the intended production design.
    paragraph_after(arch.find('h2'), 'Target production architecture. The grant completes and audits these module boundaries before the core is deployed without upgradeability.', 'small')
    for p in arch.xpath('./p'):
        text=''.join(p.itertext()).strip()
        if text.startswith('Upgradeability.'):
            content(p, '<strong>After audit.</strong> The production core will be deployed without upgradeability after the external audit and resolution of material findings. New functionality is introduced through new modules; existing loans remain in the immutable programs holding their funds. Third-party token programs may retain their own issuer and upgrade powers.')
    modules=html.fromstring('''<div class="extensibility"><h3>Universal and extensible lending</h3>
    <p>Elastic Proposal is the first offer type, not the limit of the framework. Following PWN v1.5, the target architecture separates proposal validation and product rules from shared custody and settlement. Additional proposal types that fit the agreed interfaces can be introduced as new modules without changing the deployed core.</p>
    <p>Installment products, crowdfunding and refinancing can build on these extension points. New repayment or default rules must be supported by the product interface agreed before the core becomes immutable. Milestone 1 will define and validate these interfaces; the current PoC still binds a specific Proposal and Loan pair.</p>
    <p>PWN v1.5 also provides borrower and lender hooks around loan creation and repayment, enabling integrations such as refinancing and external lender vaults. Equivalent Aleo integration points are a future extension, subject to privacy, authorisation and proving limits; hooks are not part of the demonstrated PoC.</p></div>''')
    arch.append(modules)
    privacy=section(root,'Privacy model, measured on testnet')
    privacy.set('class','privacy-section')
    for p in privacy.xpath('.//div[@class="cols keep"]/div/p'):
        if 'Required for the protocol' in ''.join(p.itertext()): p.text='Visible in the current PoC; some fields can be minimised in the production design.'
    private_chips=privacy.xpath('.//span[contains(@class,"private")]')
    names=['lender and borrower addresses in lending calls','private token input and payout records','secret authorisation salts']
    for i,chip in enumerate(private_chips):
        if i<len(names): chip.text=names[i]
        else: chip.getparent().remove(chip)
    public=privacy.xpath('.//div[@class="chips"][span[contains(@class,"public")]]')[0]
    for label in ['loan terms, amounts, links and history']:
        e=html.Element('span',{'class':'chip public'});e.text=label;public.append(e)
    last_cols=privacy.xpath('./div[@class="cols keep"]')[0]
    paragraph_after(last_cols, '<strong>Privacy first.</strong> We will minimise the loan witness and prefer private authorisation, fees and fresh salts. Public offer terms and escrow transfers can still reveal loan economics; direct offers can keep more terms private. Hiding amounts requires custody accounting without public balance changes.')
    for tr in privacy.xpath('.//tbody/tr'):
        cells=tr.findall('td')
        if cells and 'Commitment → loan' in ''.join(cells[0].itertext()):
            cells[2].text='Multiple draws do not remove this link; private fees and fresh salts reduce direct address disclosure'
    milestones=section(root,'Milestones')
    m1=milestones.xpath('.//div[contains(@class,"ms")][div[@class="n"][text()="1"]]')[0]
    scope=m1.xpath('.//p[span[text()="Scope"]]')[0]
    span=scope.find('span');span.tail=(span.tail or '').replace('and agreement of the data model and program interfaces.', 'and agreement of the data model, proposal and product extension interfaces, and privacy boundary.')
    m4=milestones.xpath('.//div[contains(@class,"ms")][div[@class="n"][text()="4"]]')[0]
    m4.xpath('.//p[span[text()="Scope"]]/span')[0].tail='  External audit of the core programs, resolution of material findings, non-upgradeable mainnet deployment with caps, SDK published as a package.'
    m4.xpath('.//p[span[text()="Validation"]]/span')[0].tail='  All critical invariants covered by tests; external audit completed and material findings resolved before mainnet deposits; at least one real loan originated, repaid and settled on mainnet end to end by an external user; deployment addresses and immutable constructor rules published.'
    callout=milestones.xpath('.//div[contains(@class,"callout ok")]/p')[0]
    content(callout, '<span class="t">Capped launch.</span> After the audit, mainnet launches with protocol-level caps on maximum commitment size and total value locked. Cap increases follow the documented governance rules for the immutable deployment.')
    questions=section(root,'Open questions')
    for li in questions.xpath('.//li'):
        text=''.join(li.itertext()).strip()
        if text.startswith('Upgradeability'): li.getparent().remove(li)
        elif text.startswith('Collateral policy'):
            content(li, '<span class="t">Collateral policy</span> Token issuers with public-burn, freeze or pause powers can affect a loan escrow. The multi-token PoC already gates assets through a Hub allowlist. Which issuer powers should V1 accept, and how should an escrow deficit affect positions in that token?')
    for p in root.xpath('//h2[text()="After the grant"]/following-sibling::p[1]'):
        content(p, 'The protocol becomes part of the PWN DAO Foundation’s maintained infrastructure, with the team behind OWN maintaining the SDK, reference application and integrations. The deployed core remains immutable. The SDK is published as an open-source package for third-party integrators.')
    extensions=section(root,'Possible extensions').xpath('.//div[@class="chips"]')[0]
    c=html.Element('span',{'class':'chip'});c.text='Borrower and lender integration hooks';extensions.append(c)
    refs=section(root,'Existing references')
    refs.set('class','references-section')
    first=refs.xpath('.//div[@class="ref"]')[0]
    content(first.xpath('.//div[@class="u"]')[0], '<a href="https://github.com/PWNDAO/pwn_protocol/tree/v1.5-withdraw-restriction">v1.5-withdraw-restriction</a>')
    first.xpath('./div')[1].text='Architecture reference: Hub, Config, modular products and proposals, installments, crowdfunding and borrower/lender hooks.'
    own=html.fromstring('''<div class="ref"><div><div class="n">OWN</div><div class="u"><a href="https://ownlabs.co/">ownlabs.co</a></div></div><div>Current team and product reference: longer-term crypto-backed lending and onchain mortgage infrastructure, building on PWN’s lending primitives.</div></div>''')
    first.addprevious(own)
    for u in refs.xpath('.//div[@class="u"]'):
        if not len(u) and u.text:
            url=u.text.strip();content(u,f'<a href="https://{url}">{url}</a>')
    css=html.Element('style')
    css.text='''a { color: var(--accent-2); text-decoration: none; } .team-section p { margin-bottom: 7pt; } .ref .u { overflow-wrap: anywhere; } .extensibility { margin-top: 10pt; }
    .privacy-section p { font-size: 9.6pt; line-height: 1.45; margin-bottom: 7pt; }
    .privacy-section .chip { font-size: 8.2pt; padding: 3pt 7pt; }
    .privacy-section table { font-size: 9pt !important; line-height: 1.35; }
    .privacy-section td { padding-top: 5pt; padding-bottom: 5pt; }'''
    css.text+='''\n.references-section .ref {font-size: 9.5pt; line-height: 1.45; padding-top: 8pt; padding-bottom: 8pt;}'''
    for weight in [400,500,600,700]:
        css.text+=f"\n@font-face {{font-family: Inter; font-style: normal; font-weight: {weight}; src: url('grant-assets-v5/inter-{weight}.ttf') format('truetype');}}"
    root.find('head').append(css)
    OUT.write_text('<!DOCTYPE html>\n'+html.tostring(root,encoding='unicode',method='html'))
    evidence=dict(base_source=str(SOURCE),base_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(), output=str(OUT),
      scope=['OWN and PWN DAO Foundation context','team','v1.5-withdraw-restriction reference','proposal and product extensibility','future hooks','post-audit immutability','privacy corrections'],
      unchanged=['grant budget and durations','original source stylesheet','original illustration layouts','PoC feasibility and performance sections'])
    (DOCS/'research-2026-10-07'/'grant-v5-edit-scope.json').write_text(json.dumps(evidence,indent=2))
    print(OUT)

if __name__=='__main__': main()
