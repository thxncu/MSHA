# Online Resource 2: reproducibility package

**Repeat ground-control citations after administrative closure: inspection sequences and recorded violation classifications in United States mines**

## Scope

This package reproduces the descriptive closure-pathway analyses, all numeric tables in the article and Online Resource 1, and Figures S1–S2. Table 4 is an evidence-to-reporting interpretation table, not an estimated intervention effect. The package contains no estimates of injury reduction, causal effects of correction, or optimal inspection schedules.

The selected cohort comprises 4,459 episodes at 3,396 mines. The four-opportunity primary outcomes are 1,201 observed repeats, 2,306 completed nonciting sequences, and 952 pathway exits. Exit categories retain alternative citation routes separately from absent or ambiguous observation. Data fields are defined in `documentation/DATA_DICTIONARY.md`; algorithmic details and outcome boundaries appear in the article and Online Resource 1.

## Installation

Use Python 3.11 or newer. The exact environment tested is recorded in `environment.json`.

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Workflow 1: regenerate outputs from included analysis-ready records

```bash
python reproduce.py --mode derived --output-dir reproduced_derived
```

The workflow reads the included linked episodes, inspection opportunities, independent inspection schedules, and first all-type detections. It recalculates the mine-cluster bootstrap intervals, descriptive contrasts, sensitivity tables, and figures. It does **not** independently reconstruct the original source linkage; use Workflow 2 for that task. Pickle files are generated only as local intermediate caches, not supplied as required inputs.

## Workflow 2: reconstruct from the identified source archive

```bash
python reproduce.py --mode raw --source-zip "/path/to/for_share(1).zip" --output-dir reproduced_raw
```

The enclosing source archive is not duplicated in this package. Its exact SHA-256 digest, byte count, and required members are recorded in `source_manifest.json`. It contains `raw/violations.zip` and `raw/inspections.zip`. The runner checks the archive and stops if it differs. A fresh download from the public MSHA portal is not the same historical snapshot. Access to the identified source archive is required for exact source-to-output reproduction.

Raw mode rereads 3,103,998 violation rows and 1,161,292 inspection rows, reconstructs operator spells and eligible closure episodes, verifies constituent classifications and dates, creates post-closure pathways, computes schedules independent of detected recurrence, and then generates the same final outputs. Source extraction reads only the two explicitly named members. Allow disk space for those files and intermediate data. The runner never overwrites a nonempty output directory.

## Outputs

- `results/tables/Table_1.csv` to `Table_4.csv`: main tables.
- `results/tables/Table_S1.csv` to `Table_S7.csv`: supplementary tables.
- `results/figures/Figure_S1.png` and `Figure_S2.png`, with vector PDF counterparts: supplementary figures.
- `results/path_metrics_cluster_CI.csv`: primary and subgroup proportions with denominators.
- `results/path_sensitivities_cluster_CI.csv`: observation-definition sensitivities.
- `results/inspection_opportunity_curve.csv`: opportunity-specific observed counts, not population cumulative risk.
- `results/severity_transition_counts.csv`, `paired_severity_change.csv`, and `observed_detection_times.csv`: classification and recorded timing outputs.
- `results/validation.json`: count, sequence, pathway-category, and numerical reproduction checks.
- Raw mode additionally produces `raw_linkage_qa.json`, `followup_schedule_qa.json`, and source/cohort intermediate records.

The `expected` directory is used only after estimation to check reproduction, never as an input to calculate a statistic. Comparisons use absolute tolerance 1e-12 and relative tolerance 1e-10. Minor graphics differences across platforms do not alter data values. The source-linked and derived workflows can produce different unused intermediate columns; reported tables and estimates are checked against the same numeric reference outputs.

The article-to-output mapping is documented in `documentation/OUTPUT_MAP.md`. Precomputed comparison tables and figures are included in `reference_outputs`; both workflows regenerate them from records.

## Statistical definitions

Index inspections start in 2008–2024; observations end on 31 December 2025. Provision matching retains exact suffixes. The follow-up start date is the later of inspection completion and the latest constituent termination. Follow-up requires completed, nonoverlapping E01 inspections strictly after that date within the observed operating spell. Each episode ends at its first eligible repeat or pathway exit. Same-provision citations outside the selected pathway are checked even when no later eligible E01 record exists. They are not recoded as no citation or attributed to an operator-only exit.

S&S means significant and substantial and is defined from affirmative recorded `SIG_SUB`. Classifications are values in the supplied snapshot, not a complete history of assessments and amendments. A bundle includes S&S if at least one constituent record is affirmative. Rapid closure means every index citation terminated within zero or one calendar day, not exactly 24 hours.

Four opportunities are the primary analytical horizon; eight are descriptive sensitivity follow-up. A delayed repeat follows at least one completed nonciting opportunity. Event-conditioned shares and observed proportions among all first-inspection noncitations have different denominators. Interrupted primary pathways remain explicit. The package does not assume noninformative censoring or turn observed counts into a population recurrence probability.

Mine-cluster percentile intervals use 3,000 resamples. Seeds are 20261007 for primary/scoped proportions, 20261008 for observation-definition sensitivities, and 20261009 for paired classification differences. All episodes of a resampled mine remain together. These intervals address conditional resampling variation, not exploratory selection, missing data, source revision, or causal identification.


## Composition and common-mix standardization

`code/07_composition.py` produces Tables S6–S7 from the same linked episodes and inspection records. Table S6 describes recorded characteristics of each observed set. Table S7 reports unstandardized fractions and direct standardization across 16 baseline strata: regulatory part (56, 57, 75, 77), index S&S group, and index period (2008–2016, 2017–2024). The reference weights are the stratum shares among the 4,159 episodes observed at opportunity 1. Each later fraction uses observed within-stratum fractions and the reference weights.

The mine-cluster bootstrap uses 3,000 draws and seed 20261010. Reference shares are recalculated in each draw. The code checks for missing attributes, duplicate episode-opportunity rows, empty reference cells, and empty resample cells; it stops rather than dropping them silently. The original minimum opportunity-by-stratum cell size is 21. Cell counts and weights are written to `results/standardization_cells.csv`. Additional outputs are `composition_by_opportunity.csv`, `standardized_observed_fractions.csv`, and `composition_validation.json`.

These calculations describe the observed sets. They neither supply missing follow-up outcomes nor control mine size, production, geology, individual inspectors, or unmeasured selection within strata. They are not estimates of cumulative incidence, individual improvement, or causal effects. The enclosing archive contains employment, production, mine, and accident files that are not used by these workflows. `documentation/COVARIATE_SCOPE.md` distinguishes unused sources from unavailable measurements and defines the endpoint-office restriction. No inspector-specific adjustment or detection-probability model is implemented.

## Source acknowledgement and reuse

The underlying records originate from the United States Mine Safety and Health Administration public-data program. No personal miner identifiers are included. Mine and administrative event identifiers are retained for scientific linkage. The archive and analysis-ready records should be handled under applicable source-data terms. The package does not claim copyright over government source records.
