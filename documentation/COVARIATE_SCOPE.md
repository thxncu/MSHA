# Covariate coverage and detection limits

## Analysis scope

The direct standardization uses only regulatory part, index S&S, and index period. It does not adjust employment, production, ground conditions, individual inspectors, or exposure changes. Available data that were not linked must be distinguished from variables absent from the supplied files. The main target remains the distribution of recorded inspection sequences, not a hazard-onset rate or a calibrated risk score.

## Employment and production

The enclosing source archive includes `raw/operator_quarterly.zip`. Its supplied fields include `MINE_ID`, `SUBUNIT_CD`, `CAL_YR`, `CAL_QTR`, `AVG_EMPLOYEE_CNT`, `HOURS_WORKED`, and `COAL_PRODUCTION`. Rows refer to mine-subunit-quarter records; the file has no operator identifier. These records are not inputs to the standardization or to either reproduction workflow. A separate linkage would require a specified pre-inspection period, subunit aggregation, missing-data handling, and checks for operator changes within quarters.

`COAL_PRODUCTION` records quarterly coal tonnage. MSHA does not require metal/nonmetal operators to report production. A missing or zero coal-production entry must not be interpreted as the mine's metal/nonmetal output.

## Mine attributes and accident history

`raw/mines.zip` includes current mine type, current status, current operator, and `NO_EMPLOYEES`. The file does not provide a dated history of every attribute. Its snapshot values should not be copied to each historical inspection without evidence that they applied then.

`raw/accidents.zip` includes accident dates, mine and operator identifiers, classifications, and narratives. A pre-inspection reported ground-fall history could be derived under explicit selection and linkage rules. Reports do not measure geology at every inspected location, and the absence of a reported fall does not establish stable ground. Neither of these files is an input to the reported standardization.

## Inspectors and recorded time

The supplied inspection file includes `INSPECT_OFFICE_CD`, `NBR_INSPECTOR`, and aggregate inspection-time fields named `SUM(TOTAL_INSP_HOURS)` and `SUM(TOTAL_ON_SITE_HOURS)`. The official data dictionary names the count `NBR_INSPECTORS` and the corresponding time fields without `SUM(...)`. These are counts or time totals, not person identifiers. Neither the supplied inspection nor violation file has an individual inspector identifier. Individual-inspector fixed effects therefore cannot be fitted from these files alone.

The same-office sensitivity in `code/05_sensitivity.py` compares the index office with the office recorded for the first eligible repeat. It does not require each intervening inspection to have that office and does not hold inspection personnel constant. It conditions on an observed repeat with matching endpoint offices.

On-site hours include citation/order writing. Total hours also include off-site writing, travel, and other tasks. Those totals do not isolate search effort from documentation of findings. The reported analyses do not estimate independent search intensity or a calibrated probability of detecting a physical hazard. Inspector assignments would improve personnel comparisons, but estimating detection would also require independently assessed conditions or another justified validation design.

## Official source definitions

- MSHA data portal: https://arlweb.msha.gov/OpenGovernmentData/OGIMSHA.asp
- Operator-quarterly employment/production: https://arlweb.msha.gov/OpenGovernmentData/DataSets/MineSProdQuarterly_Definition_File.txt
- Mines: https://arlweb.msha.gov/OpenGovernmentData/DataSets/Mines_Definition_File.txt
- Accidents: https://arlweb.msha.gov/OpenGovernmentData/DataSets/Accidents_Definition_File.txt
- Inspections: https://arlweb.msha.gov/OpenGovernmentData/DataSets/Inspections_Definition_File.txt
- Violations: https://arlweb.msha.gov/OpenGovernmentData/DataSets/violations_Definition_File.txt

Accessed 9 October 2026. Source headers refer to the archive identified in `source_manifest.json`; current public downloads may differ.
