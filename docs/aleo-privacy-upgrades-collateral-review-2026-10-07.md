# Aleo lending privacy upgrady a kolaterál

Podklad k úpravě grantového draftu · Ověřeno 7. října 2026

**Současný PoC skrývá adresy v kontrolovaných lending transakcích, ale neskrývá ekonomické podmínky ani historii konkrétní půjčky.** Více čerpání z jednoho commitmentu nezruší veřejnou vazbu na nabídku. Produkční core lze po auditu nasadit bez upgradů, ale tím nezmizí oprávnění emitentů tokenů. Níže odděluji zjištění z kódu, aktuální veřejná data a návrhy dalšího designu.

Anglická verze draftu je v `private-lending-aleo-grant-draft-v4.md` a stejnojmenném DOCX. Dokumenty lze importovat do Google Docs; používají běžné nadpisy, odstavce a tabulky. Původní HTML a PDF zůstaly zachovány. Tato rešerše je pracovní podklad pro Jana a Šimona, nikoli součást grantové žádosti.

## Co se změnilo v draftu

- Tým je hned po úvodu. Jan je popsán jako engineer se čtyřmi lety práce na PWN DeFi lending aplikaci. To zdůrazňuje konkrétní crypto zkušenost bez přisuzování neověřené auditní či kontraktové specializace.
- Přibyly ověřené LinkedIn a GitHub profily Jana a Šimona a dodaný Josefův LinkedIn. Josefův osobní GitHub se nepodařilo spolehlivě určit; nevymýšlel jsem ho. Společný odkaz vede na PWN protocol repository.
- Zmizela otevřená otázka o třech až šesti měsících upgradability. Po dokončení externího auditu a odstranění podstatných nálezů má následovat neměnný produkční deployment. Audit musí být dokončen před přijímáním mainnet vkladů; samotná nabídka auditu nestačí.
- Opravil jsem tvrzení o privátních podmínkách půjčky, repayment history a anonymitě více draws. Rozlišuji doložené chování, cílovou privacy a informace odvoditelné z jiných částí transakce.
- Rozlišuji veřejně testovaný single-pair předchůdce od současné multi-token verze ověřované lokálně. Rozpočet $85,000 a 17 týdnů zůstal zachován.

U Šimona jsem ponechal roli dodanou uživatelem. Jeho veřejný LinkedIn popisuje CTO u PWN jako dřívější roli, proto je vhodné před odesláním potvrdit aktuální označení u PWN a OWN. Janův LinkedIn přímo uvádí čtyřletou práci na PWN a propojuje jeho GitHub. [Janův profil](https://cz.linkedin.com/in/jan-miksik/en), [Šimonův profil](https://cz.linkedin.com/in/simon-kozak).

## Proč více draws samo o sobě nezlepšuje anonymitu

Představme si commitment C, ze kterého vzniknou půjčky L1 a L2. V PoC je C součástí veřejného witnessu obou půjček. Pozorovatel proto přesně ví, že L1 a L2 pocházejí ze stejného funding commitmentu. Veřejný lender authorization hash poskytuje další vazbu. Více borrowerů není více lenderů a nevytváří pro lendera anonymity set.

Když se adresa lendera podaří přiřadit k C, například přes veřejný fee payment nebo korelaci shieldingu, přiřadí se tím i všechny půjčky z C. Více draws může dokonce rozšířit následky jednoho deanonymizujícího pozorování. Pokud lender identifikován není, zůstává skrytá jeho adresa, ale cluster jeho půjček je viditelný.

Oprávněný přínos elastic proposal je provozní: lender financuje nabídku jednou a nemusí podepisovat každý draw. Tím odpadají další příležitosti k přímému veřejnému funding podpisu. Nelze z toho bez měření vyvodit vyšší anonymitu než u několika samostatných commitmentů používajících stejnou fee a shielding strategii.

V draftu proto píšu, že více draws amortizuje funding transakci, nikoli že ztěžuje dohledání lendera. Silnější unlinkability by vyžadovala odstranit přímé vazby na commitment i lender pseudonym a současně řešit veřejné změny likvidity, částky a časování. Pouhé nové loan ID nestačí.

Opírám se o `PRIVACY.md`, veřejné `Loan.commitment_id` a `lender_auth` v `pwn_loan_poc/src/main.leo` a o terms a accounting v `pwn_proposal_poc/src/main.leo`. Jde o analýzu konkrétního projektu; nebyl proveden nový anonymity experiment.

## Proposal versus loan

**Proposal** je nabídka a financování, ze kterých se teprve mohou vytvořit půjčky. Obsahuje limity draws, asset pair, poměry kolaterálu a splácení, APR, délku půjčky a expiry nabídky. Commitment je její financovaná instance. Veřejná nabídka musí zájemci poskytovat dost informací k rozhodnutí a objevování.

**Loan** je konkrétní závazek po acceptance. Má vlastní principal, kolaterál, repayment pravidlo a maturity. Expiry proposal ukončuje nové draws; maturity loan určuje, od kdy lender může claimnout kolaterál. Cancellation nabídky vrací nevyužitou kapacitu a neruší aktivní půjčky. Repayment kapacitu nabídky automaticky neobnovuje.

V aktuálním kódu je `Loan` veřejný struct/witness, nikoli soukromý Aleo record s kompletními podmínkami. Mapování `loans` drží jeho hash, začátek, maturity a status, ale to neskrývá data publikovaná v transakcích. Stejně tak veřejný terms hash není náhradou za privacy, pokud celé terms vyšly v transakci.

## Co lze privatizovat a jaký to má skutečný přínos

| Údaj | Současný stav | Preferovaný směr a zbývající inference |
| --- | --- | --- |
| Lender a borrower adresa | V kontrolovaných calls s private fee není adresa; jsou veřejné salted auth hashe | Zachovat private authorization, private fees a čerstvý salt pro každou pozici; shielding a síťová metadata mohou adresu prozradit |
| Podmínky veřejné nabídky | Veřejné terms v transakcích a veřejné funding údaje | Veřejně zobrazit potřebné offer terms; individuální witness minimalizovat. Veřejný poměr a draw odhalí výsledný kolaterál |
| Acceptor přímé nabídky | Direct offers nejsou hotové | Soukromý důkaz identity/oprávnění proti blinded commitmentu; nepublikovat adresu příjemce. Samostatně vyřešit doručení witnessu |
| Principal a kolaterál | Veřejné token futures, escrow deltas i witness | Skrytý witness odstraní duplicitu, ne veřejné částky. Plná privacy vyžaduje změnu custody/token accounting nebo jiný settlement flow |
| Repayment a APR | Veřejné loan/proposal parametry a převáděné částky | U neveřejně dohodnuté nabídky držet terms v privátním witnessu a dokazovat správnost výpočtu; konečný token převod zůstává veřejný |
| Maturity a začátek | Veřejné loan state a acceptance block | ZK důkaz podmínky vůči veřejnému časovému anchoru je kandidát k ověření. Pokud je offer duration veřejná, maturity lze odvodit z acceptance |
| Loan ID a status | Veřejně propojují origination a settlement | Opaque commitment a jednorázový nullifier mohou omezit explicitní historii, ale nevyloučí vazby přes token amounts a grouping |
| Commitment vazba | Přímá a veřejná | Vyžaduje přepracovat proposal accounting a čerpání. Dokud se mění konkrétní veřejná available_credit, vazba zůstává |
| Payout records | Šifrované pro příslušného vlastníka | Zachovat; private record výstup ale automaticky neschová veřejnou částku předchozího převodu |
| Compliance informace | USDCx/USAD vydávají compliance records určenému operátorovi | Rozlišit public-observer privacy od privacy vůči oprávněnému compliance příjemci |

Tabulka popisuje návrhy, ne implementované záruky. Pro privátní witness musí hash/commitment obsahovat čerstvé zaslepení, aby malý prostor možných terms nešel hádat. Vlastník musí mít data dostupná pro splácení či claim; druhé straně je potřebné informace nutné bezpečně doručit. Nullifiery a závazky musí zabránit dvojímu settlementu a replayi.

Největší realistický krátkodobý přínos je omezení přímého spojení **konkrétní veřejné adresy s dluhovou pozicí**, zejména při private fees a čerstvých saltech. To je užitečné i s veřejnými částkami. Nedává to však obecnou anonymitu: identifikace jedné pozice může zpětně odhalit její veřejnou historii.

Silnější privacy mají potenciálně **direct offers**: jejich dohodnuté terms nemusí být ve veřejném katalogu. U open elastic proposals jsou economic terms často rekonstruovatelné, protože známe nabídku, draw a block acceptance. Šifrování těchto údajů přinese méně reálného utajení než odstranění publikace údajů, které nelze odvodit jinde.

V této custody architektuře principal a collateral nelze schovat pouhým přepnutím `public` na private. Native credits i zkontrolované token interfaces provádějí custody přes veřejné balances a veřejné finalization amounts. Aleo program navíc nemá vlastní signing key pro běžné utrácení recordu drženého na jeho programové adrese. Alternativní privátní custody je nový designový problém, který musí prokázat solventnost, jednostranné výstupy a settlement bez lendera online.

Proto doporučuji pro V1 slíbit minimalizovaný witness, privátní participant authorization, privátní direct acceptor a poctivou privacy matrix. Fully private amounts mají být výzkumný výstup nebo další etapa, dokud neexistuje ověřený token/custody flow. Neměřil jsem procento anonymizace ani velikost anonymity setu.

## Co může změnit upgrade Aleo programu

Upgrade mění kód pod stejným program ID a využívá dosavadní stav. Může přepsat logiku existujících entry funkcí a jejich finalization a přidat nové funkce, typy, records, mappings či imports. Nesmí změnit existující entry signatury, odstranit komponenty, změnit strukturu existujících records/mappings ani změnit constructor. Inlined helper se může změnit jako součást znovu kompilovaného těla; existující neinline helper/closure má omezení. [Oficiální Leo pravidla](https://docs.leo-lang.org/guides/upgradability#the-rules-what-you-can-and-cannot-change).

Pro lending to znamená změnu authorization checks, účetních kontrol, repayment výpočtu, podmínek defaultu, cíle payoutu nebo toho, zda settlement vůbec projde. Zachovaný datový formát není zachovaná ekonomická záruka. Nová funkce může pracovat s dosavadními veřejnými zůstatky a mapping hodnotami, pokud ji tokenová oprávnění dovolí.

Upgrade nepřepíše minulou chain historii a sám nedá adminovi cizí private key nebo schopnost dešifrovat libovolné soukromé records. Může ale změnit budoucí pravidla aplikace tak, že uživatel o přístup k prostředkům přijde. Také změna dependency může poškodit settlement neměnného programu. Tento rozdíl mezi neměnným schema a změnitelnou logikou zdůrazňuje i [ARC 6](https://github.com/ProvableHQ/ARCs/discussions/94).

Constructor je trvalá brána upgradu. `@noupgrade` jej uzamkne na edition 0. Staré programy bez constructoru jsou aplikačně neupgradovatelné. Naproti tomu constructor kontrolující multisig approval umožňuje schválenou změnu; jeho účinnost může záviset i na změnitelném multisig programu. [Oficiální Leo guide](https://docs.leo-lang.org/guides/upgradability).

U současného PWN PoC jsou Config, Hub, Proposal i Loan upgradeable. Constructor kontroluje upgrader adresu a schedule v Config s prodlevou 720 blocks. Schedule váže module a edition, nikoli checksum konkrétního schváleného kódu. Samotná prodleva nebrání změně custody pravidel a nemusí dát lenderovi možnost opustit dlouhou aktivní půjčku. Proto nelze aktuální PoC prezentovat jako core, který governance nikdy nemůže změnit.

Pro nový produkční deployment po auditu doporučuji jednoduchý nezávislý `@noupgrade` constructor ve všech core programech. Existujícímu constructoru nejde dodatečně přepsat pravidlo na `@noupgrade`; změna designu před mainnetem znamená nové nasazení. UI/SDK a nově schvalované moduly lze rozvíjet odděleně, ale stávající escrow nesmí přes routování získat novou mutable settlement dependency.

Audit neměnného core musí prověřit dependency upgrades, freeze/pause/burn rizika tokenů a chování při nekompatibilní změně tokenu. Immutability omezuje zásahy týmu do půjček i možnosti pozdější opravy.

## Jak rozšířené jsou upgrady u hlavních programů

Stáhl jsem veřejný žebříček [Provable Explorer Programs](https://beta.explorer.provable.com/programs) a aktuální mainnet bytecode přes Provable API. Vyhodnotil jsem constructor všech programů v top 20 podle `allTimeData` a top 20 podle `weeklyData`, plus relevantní tokeny a governance dependencies. Tabulky a hashované kopie jsou uložené v `research-2026-10-07`.

**Historická top 20: 1 z 20 má v bytecodu povolenou cestu upgradu.** Prvních pět tvoří `credits.aleo`, Puzzle coin, token registry, Puzzle ticket a Pondo; všechny nemají constructor. Jediný upgradeable v top 20 je Shield wrapped USDCx na 19. místě. U credits jde o aplikační upgrade mechanismus; změny samotného protokolu/VM konsensem jsou jiná věc.

**Týdenní top 20 z exploreru: 15 z 20 má cestu upgradu.** Tyto programy tvoří 91,7 % součtu calls jen v tomto vzorku. Týdenní dataset neobsahuje `credits.aleo`; přesné hranice období a úplnost datasetu nebyly nezávisle ověřeny. Není to procento všech programů, celé sítě ani TVL. Pro aktuální aktivní DeFi je však týdenní vzorek relevantnější než historie dominovaná staršími immutable aplikacemi.

USDCx, USAD, ARC-20 SOL/WBTC/ETH, Shield Swap, router a wrapped tokens mají constructor s approval cestou. U USDCx/USAD/ARC-20/Shield multisig dependencies je aktuálně `allow_upgrades: true`. Oba jUSD oracles kontrolují approval, timelock, upgrader a `upgrades_disabled`; přečtená kill-switch klíčová hodnota byla prázdná, podle `get.or_use` tedy false. EasyStaking v3 používá přímo pevně zadaného program ownera. Merkle tree a některé autojoin helpers explicitně kontrolují edition 0.

Tato klasifikace znamená, že kód umožňuje schválený upgrade; není testem vykonání konkrétního upgradu. Neauditoval jsem celý governance graph ani práva všech signerů. Nenasazoval jsem žádný kontrakt.

## Burn kolaterálu u významných tokenů a aplikací

| Program nebo asset | Zjištěné burn oprávnění | Důsledek pro escrow |
| --- | --- | --- |
| Native ALEO v credits.aleo | Bez funkce issuer burn pro libovolný account | V bytecodu není analog token-admin spálení cizího collateral balance; stále záleží na lending logice |
| Token registry assets | Admin konkrétního tokenu nebo role 2/3 může burn_public proti cílovému accountu | I immutable registry dovoluje issuer burn veřejného escrow; je třeba auditovat admin tokenu a jeho dosažitelné calls |
| USDCx a USAD | BURNER bit 2 dovoluje burn_public libovolného veřejného balance, pokud token není paused | Lending escrow nemá výjimku. ADMIN může přidělovat role, upgrade tokenu může změnit další pravidla |
| ARC-20 SOL WBTC a ETH | Obdobná role-based burn_public proti owner address | Public escrow je vystavené issuer governance. Privátní record nelze touto public funkcí spálit |
| Pondo pALEO | Běžné withdrawal calls pálí registry pALEO volajícího/signera a řeší výběr ALEO | Redemption burn není automaticky confiscation libovolného escrow. Další schopnosti určuje token admin a role registry |
| Shield Swap LP position | burn spotřebuje PositionNFT a vyžaduje liquidity 0 a žádné tokens owed | Mazání prázdné LP pozice nepálí aktivní podkladová aktiva půjčky |
| Shield wrapped USDCx a credits | V kontrolovaném bytecodu není obecná issuer burn_public; burn_empty_record vyžaduje amount 0 | Wrap/withdraw snižují wrapped supply při výběru; stále existuje upgrade riziko a u USDCx riziko underlying custody |

Zdroje jsou konkrétní mainnet bytecode: [registry](https://api.explorer.provable.com/v1/mainnet/program/token_registry.aleo), [USDCx](https://api.explorer.provable.com/v1/mainnet/program/usdcx_stablecoin.aleo), [USAD](https://api.explorer.provable.com/v1/mainnet/program/usad_stablecoin.aleo), [SOL](https://api.explorer.provable.com/v1/mainnet/program/arc20_sol.aleo), [WBTC](https://api.explorer.provable.com/v1/mainnet/program/arc20_wbtc.aleo), [ETH](https://api.explorer.provable.com/v1/mainnet/program/arc20_eth.aleo), [Pondo](https://api.explorer.provable.com/v1/mainnet/program/pondo_protocol.aleo), [Shield Swap](https://api.explorer.provable.com/v1/mainnet/program/shield_swap.aleo), [Shield wrapped USDCx](https://api.explorer.provable.com/v1/mainnet/program/shield_swap_arc20_wrapped_usdcx.aleo). Kopie i SHA256 jsou součástí podkladů.

### USDCx aktuální role a rozdíl mezi burn a bridge

Znovu jsem přečetl čtyři známé role adresy z dřívější bezpečnostní kontroly: ADMIN má 8, PAUSER 4 a dva bridge programy 3, tedy MINTER i BURNER. Jde o potvrzení těchto klíčů, nikoli o kompletní enumeraci rolí; nemohu tvrdit, že jiné BURNER adresy neexistují.

Aktuální `usdcx_bridge` a `usdcx_bridge_v2` při běžném veřejném výběru pálí USDCx `self.caller`. V2 má také cestu `self.signer`. Uživatel tedy normálně pálí svůj zůstatek pro bridge redemption; nevybírá libovolnou cizí escrow adresu. Tokenová `burn_public` samotná ale owner/caller shodu nevyžaduje. ADMIN může přidělit BURNER jiné adrese bez timelock kontroly v této role-update funkci. To je reálné governance riziko veřejného escrow, i když se běžný bridge chová úžeji.

Privátní burn naopak spotřebovává konkrétní Token record a vyžaduje jeho spend authorization i BURNER oprávnění volajícího. Nelze jej popsat jako funkci, kterou vždy může sám vykonat libovolný držitel. Issuer bez součinnosti/spend authorization vlastníka nemůže pouze adresou zacílit existující private record. Změna token logiky může nicméně omezit jeho budoucí použitelnost.

### Registry tokens a Pondo

Registry metadata pro pALEO i wrapped credits aktuálně uvádějí token admin, `external_authorization_required: false` a jejich aktuální supply. Tato volba odstraňuje externí transfer authorization požadavek; neodstraňuje admin burn oprávnění.

Pokud je admin adresa programová, není to automaticky účet, jehož private key někdo má. Reálné vyvolání burn závisí na dosažitelných entry points admin programu a na dalších přidělených rolích. Pondo withdrawal kód používá caller/signer a nelze jej z této kontroly označit za libovolně dostupný confiscation endpoint. Plný audit všech registry role entries a všech token admin programů nebyl součástí vzorku.

### Dopad na náš lending core

Issuer burn sníží skutečný veřejný token reserve, ale nezmenší automaticky evidované nároky půjček. Reserve check současné multi-token implementace deficit detekuje a nepustí některé payouty. Nevytvoří náhradní kolaterál a neurčuje, který lender ponese ztrátu. Deficit jednoho tokenu může postihnout více pozic v jeho sdíleném escrow; jiné tokeny mají oddělené accounting.

Freeze a pause prostředky nespálí, ale mohou zablokovat převod, splácení či claim. Bridge burn je běžně redemption. Burn prázdného LP tokenu je odstranění již vybrané pozice. Tyto čtyři věci se nemají slučovat do tvrzení, že velké Aleo kontrakty běžně pálí cizí kolaterál.

Před mainnetem doporučuji contract-level asset admission podle konkrétního programu a jeho governance, zveřejněný přehled issuer powers, deficit pravidlo a ověření toho, zda token upgrade může znefunkčnit settlement immutable core. Skrytí loan witnessu toto custody riziko nesnižuje.

## Podklady a omezení ověření

`research-2026-10-07/program-evidence.json` obsahuje program IDs, zdrojové API adresy, SHA256 a constructors. `ranking.json` uchovává historický i týdenní dataset exploreru. `state-evidence.json` obsahuje čtené governance/role klíče a pozorovanou výšku 22,608,879. Čtení různých endpointů nebyla atomická na jednom blocku.

Bytecode byl získán přímo z veřejného mainnet API. Jeho inspection dokládá povolené operace a jejich guardy, nikoli skutečné případy konfiskace nebo jejich četnost. Burn historii celého ekosystému ani úplnou enumeraci všech tokenových rolí jsem neměřil. `usad_bridge.aleo` nebyl pod tímto ID nalezen; o jeho současném deploymentu nedělám závěr.
