# Test 6: do Qloo's audience tags describe who is actually in an area? Pre-registered protocol

Registered 2026-10-10, before any census, jobs or hotel data was downloaded and before any Qloo audience
query for this test. The git commit adding this file is the timestamp.

## Why this test exists

Tests 1, 2 and 4 asked whether Qloo predicts where restaurants open; it does not add to city records. But
the product uses Qloo for something else: describing an area's audience (its location profile carries
"customer identity" tags such as Affluent Diners or Young Adults), and a planned scout mode would use those
tags to shortlist neighbourhoods for a founder's target customer. That description has never been checked
against anything outside Qloo. This test checks it.

## Units

2020 Neighborhood Tabulation Areas (NYC Planning, dataset 9nt8-h7nd) in Brooklyn, Queens, Manhattan and the
Bronx, keeping residential NTAs (NTA type 0) with at least 1,000 residents in the census data below.
Each NTA is represented by one point inside it (shapely `representative_point`).

## Qloo measure

For each NTA point, one `/v2/insights` call with `filter.type=urn:tag`, `signal.location=POINT(lon lat)`
(default radius, as in the product) and `filter.results.tags` = the seven tags below; the measure is each
tag's returned `query.affinity`. An NTA where a tag returns no affinity is dropped for that pair only.

## Pairs (tag and independent measure, fixed now)

| # | Qloo tag | Independent measure | Source |
|---|---|---|---|
| 1 | Affluent Diners (`urn:tag:customer_identity:qloo:affluent_diners`) | Median household income, NTA value = household-weighted mean of tract medians (B19013, weights B11001) | ACS 2019 to 2023 5-year, tracts |
| 2 | Young Adults (`...:young_adults`) | Share of residents aged 20 to 34 (B01001) | ACS 5-year |
| 3 | College Students (`...:college_students`) | Share of residents aged 3+ enrolled in college or graduate school (B14001_008 + B14001_009 over B14001_001) | ACS 5-year |
| 4 | Families (`...:families`) | Share of households with one or more people under 18 (B11005_002 over B11005_001) | ACS 5-year |
| 5 | Seniors (`...:seniors`) | Share of residents aged 65+ (B01001) | ACS 5-year |
| 6 | Business Professionals (`...:business_professionals`) | Jobs located in the NTA per square km, log (LODES workplace area characteristics, all jobs, latest year available, blocks assigned to NTAs through their 2020 tract) | LEHD LODES 8 |
| 7 | Tourists (`...:tourists`) | Hotel properties per square km, log(1 + x) (Hotels Properties Citywide, tjus-cn27, current pull) | NYC Open Data |

Tracts are assigned to NTAs with NYC Planning's 2020 tract-to-NTA equivalency (or, if unavailable, by the
tract's representative point falling inside the NTA polygon; the method used is reported).

## Primary analysis

For each pair: Spearman rho between the Qloo affinity and the independent measure across NTAs. 95% interval
by cluster bootstrap, resampling 2020 Community District Tabulation Areas (2,000 resamples, seed 0).

A pair is **validated** if rho >= 0.30 and the interval's lower bound is above 0.

## Secondary (reported, not decisive)

- Discriminant check: for each independent measure, the rank of its own tag's rho among all seven tags'
  rho with that measure (1 = its own tag tracks it best).
- Each tag's rho with every measure, as a 7 x 7 table.

## Decision rule (all outcomes decided now)

- **5 or more of 7 validated:** we may say Qloo's audience tags track independent measures of who is in an
  area, citing this table. Scout mode may use validated tags to shortlist neighbourhoods, each match shown
  with its rho.
- **2 to 4 validated:** only validated tags may be used for neighbourhood matching, each labelled with its
  rho; no general claim about Qloo's audience tags.
- **1 or none:** no audience matching in scout mode; the page says Qloo's audience tags did not match
  independent data.

The positioning brief's evidence is not changed by this test (it is the configuration Test 3 rates); the
result is shown beside it.

## Known limitations

Qloo tags describe the audience of an area's venues (visitors included), while census measures describe
residents; pairs 6 and 7 use non-resident measures for that reason. ACS values are 5-year estimates with
margins of error. Jobs and hotels are densities, not audiences. NTAs differ in size and population.

## Amendments

None.
