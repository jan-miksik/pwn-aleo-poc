# Grant market evidence

Checked **2 November 2026**. This note separates token supply, lending balances elsewhere, and demand that the proposed Aleo protocol still needs to validate.

## Suggested grant paragraph

USDCx and USAD provide a dollar-denominated asset base on Aleo: their combined on-chain supply was approximately **$4.71m at peg on 2 November 2026**. ([USDCx state](https://api.explorer.provable.com/v1/mainnet/program/usdcx_stablecoin.aleo/mapping/token_info/true), [USAD state](https://api.explorer.provable.com/v1/mainnet/program/usad_stablecoin.aleo/mapping/token_info/true)) Borrowing against assets is established elsewhere: Galaxy reported **$56.16bn** in crypto-collateralized loans at the end of Q2 2026, including **$20.43bn in DeFi**; Federal Reserve researchers estimated **$138bn** in US securities-based loans in Q1 2024. ([Galaxy](https://www.galaxy.com/insights/research/crypto-leverage-report-q2-2026-defi-lending-decline-futures-open-interest), [Federal Reserve](https://www.federalreserve.gov/econres/notes/feds-notes/estimating-securities-based-loans-outstanding-20240802.html)) The initial audience is ALEO holders seeking liquidity without selling and stablecoin holders willing to fund bilateral loans. These figures establish assets and adjacent market scale; demand for this protocol must be validated through pilot lenders, borrowers and completed loans.

## Aleo supply: direct mainnet observation

Read Provable's public mainnet `token_info[true]` mappings on **2026-11-02 at 14:15:32 UTC**. Both responses reported `decimals: 6u8`. Divide the raw `supply` by `10^6` to obtain token units.

| Asset | Raw supply (`u128`) | Token units | Primary source |
| --- | ---: | ---: | --- |
| USDCx | 4,258,945,404,803 | 4,258,945.404803 | [Token state](https://api.explorer.provable.com/v1/mainnet/program/usdcx_stablecoin.aleo/mapping/token_info/true) |
| USAD | 447,680,320,648 | 447,680.320648 | [Token state](https://api.explorer.provable.com/v1/mainnet/program/usad_stablecoin.aleo/mapping/token_info/true) |
| Combined | 4,706,625,725,451 | **4,706,625.725451** | Sum of the two observations |

The [latest-height endpoint](https://api.explorer.provable.com/v1/mainnet/block/height/latest) returned **23,389,743** immediately before and after the mapping reads. All four HTTP responses were dated 14:15:32 GMT. These were latest-state queries, not queries pinned to a historical block; future reads may differ.

Aleo describes [USDCx](https://aleo.org/usdcx/) as backed 1:1 by USDC in Circle xReserve and [USAD](https://aleo.org/usad/) as backed 1:1 by USDG. Thus **$4.71m is a nominal value at the dollar pegs**, not a separately measured market valuation or verification of reserves. Total token supply does not establish how much is available to lend, already deployed, idle, or held by prospective users. It also does not measure private balances separately.

## Broader lending context

| Context | Observation date | Verified figure | Source and publication date |
| --- | --- | --- | --- |
| Crypto-collateralized lending | 30 June 2026 | **$56.16bn** outstanding across Galaxy's categories; **$20.43bn** on DeFi lending applications | [Galaxy Research, *The State of Crypto Leverage Q2 2026*](https://www.galaxy.com/insights/research/crypto-leverage-report-q2-2026-defi-lending-decline-futures-open-interest), 17 August 2026 |
| US securities-based lending | Q1 2024 | Estimated **$138bn** outstanding | [Bruce and Hannon, Federal Reserve FEDS Notes, *Estimating Securities-Based Loans Outstanding*](https://www.federalreserve.gov/econres/notes/feds-notes/estimating-securities-based-loans-outstanding-20240802.html), 2 August 2024 |

Galaxy's total includes CeFi, DeFi applications and crypto-backed CDP stablecoins. Its methodology acknowledges possible double counting between categories and uneven CeFi disclosures. These are outstanding balances, not annual originations, and the total should not be described as entirely on public ledgers. This review verified Q2 figures; it does not present them as November balances. ([Methodology and category discussion](https://www.galaxy.com/insights/research/crypto-leverage-report-q2-2026-defi-lending-decline-futures-open-interest))

The Federal Reserve figure is a bank-sector estimate derived from several datasets, excludes margin lending and may miss non-bank loans without a bank partner. It supports an adjacent use case—obtaining liquidity without selling an investment portfolio—but does not measure demand for Aleo or establish equivalent collateral, loan terms or customers. ([Scope, methodology and footnotes 3 and 17](https://www.federalreserve.gov/econres/notes/feds-notes/estimating-securities-based-loans-outstanding-20240802.html))

## Changes from the original proposal

Reviewed `/tmp/aleo-grant-original.txt`, its HTML source and the repository's [token-snapshot provenance](multitoken/README.md). Those token fixtures are code snapshots, not supply observations.

- Replace the original **16 October 2026 $5.0m** supply claim with the directly observed **2 November 2026 $4.71m at peg**, or retain the older figure only with its own archived primary evidence. This review did not independently revalidate the October observation.
- Keep the broader lending figures explicitly dated. Do not add these different populations together into a claimed addressable market.
- Remove unsupported assertions that all Aleo stablecoins are seeking yield, earn nothing, or will enter this protocol. Treat prospective user groups as hypotheses until supported by interviews, pilot commitments or usage.
- Do not claim “first lending market” or “no credit market” from the absence of an entry in a directory. This research did not establish exhaustive competitive coverage.
