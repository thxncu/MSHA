# Analysis-ready data dictionary

All CSV files use UTF-8; compressed files are gzip streams. Identifiers are strings, preserving leading zeros. Dates use ISO 8601; an empty value is missing, not a negative finding. Boolean fields contain True/False or missing where a future citation does not exist. An episode is a mine × observed operator spell × exact provision closure episode; an inspection may contribute to multiple provisions.

## `episode_records.csv.gz`

| Field | Meaning |
|---|---|
| episode_id | Unique selected closure-episode identifier. |
| MINE_ID | MSHA mine identifier, read as a string. |
| OPERATOR_ID | Operator identifier recorded for the index inspection. |
| PART_SECTION | Exact recorded provision, including any subparagraph. |
| EVENT_NO | Index inspection identifier. |
| n | Number of constituent index citations. |
| ss | 1 if the index bundle contains recorded S&S, otherwise 0. |
| prefix | Provision part: 56, 57, 75, or 77. |
| office | Recorded index inspection office, not an inspector identifier. |
| begin, end | Index inspection start and completion dates. |
| issue, last_issue | Earliest and latest constituent issuance dates. |
| term | Latest constituent termination date. |
| anchor | Later of index completion and latest constituent termination. |
| run | Observed operator-spell identifier constructed from inspection order. |
| run_end | Next observed operator-spell start, where recorded. |
| status | Terminal reason for the full available primary trajectory; interpret jointly with event_k and horizon. |
| n_observed_E01 | Number of eligible opportunities observed through first repeat or exit. |
| raw_n | Constituent citation count independently rejoined from violation records. |
| raw_ss | Independently linked indicator that any index citation has SIG_SUB=Y. |
| raw_ss_known | True if all constituent S&S values are known. |
| raw_term, raw_issue, raw_last_issue | Independently rejoined latest termination and earliest/latest issuance. |
| raw_uncertain | Any duplicated identifier or uncertain follow-on linkage in the bundle. |
| days_max, days_min | Maximum/minimum constituent issuance-to-termination calendar-day difference. |
| raw_days_med | Median constituent issuance-to-termination calendar-day difference. |
| fast_all1 | All constituent delays are zero or one calendar day. |

Terminal `status` codes are `E01_same_rule` (eligible first repeat), `administrative_or_no_further_E01`, `operator_change_after_last_observation`, `nonregular_same_rule` (same-provision citation outside the primary pathway, including incompatible E01 records), `ambiguous_followup`, and `overlapping_E01`. The code name `nonregular_same_rule` must not be interpreted to mean every record has a non-E01 activity code. A four-opportunity nonciting sequence is classified from its observed length even if the full trajectory later ends in citation or another exit.

## `inspection_records.csv.gz`

| Field | Meaning |
|---|---|
| episode_id, MINE_ID | Link to closure episode and mine. |
| EVENT_NO_follow | Follow-up inspection identifier. |
| follow_begin, follow_end | Follow-up inspection dates. |
| k | Eligible post-anchor inspection opportunity number, starting at 1. |
| y | 1 for first eligible exact-provision citation; 0 for an eligible noncitation. |
| follow_office | Recorded office for follow-up. |
| anchor | Episode observation origin. |
| f_raw_n | Number of constituent citations of the selected provision in a citing inspection; missing on noncitation rows. |
| f_raw_ss, f_raw_ss_known | Any affirmative S&S and completeness of constituent classification. |
| f_raw_term | Latest available termination among constituent follow-up citations; not used to define earlier exposure. |
| f_raw_issue, f_raw_last_issue | Earliest/latest follow-up issuance. |
| f_raw_uncertain | Any uncertain identifier/linkage within the follow-up bundle. |
| f_raw_serious | Auxiliary indicator derived from recorded injury-severity categories; not the article’s S&S outcome. |

Each episode contributes at most one positive row and no rows after that positive. A noncitation concerns only the selected exact provision, not absence of all violations or all physical hazards.

## `schedule_records.csv.gz`

`episode_id` links each episode to `scheduled_E01_count`, the number of nonoverlapping, completed post-anchor E01 records within its observed spell, assessed independently of primary recurrence. `complete_schedule_4` and `complete_schedule_8` indicate at least four/eight records. `schedule_4_end` and `schedule_8_end` locate the corresponding completions. These are retrospective observed schedules, not advance appointments or random assignments.

## `first_any_inspection_detection.csv.gz`

Episode identifiers, `status`, `anchor`, and `run_end` accompany the earliest post-anchor same-provision citation regardless of activity code. `first_any_issue`, `first_any_EVENT_NO`, and `first_any_activity` identify that record. `first_any_status` is `new_linkable` or `ambiguous`; missing means no record satisfying the search window, not permanent compliance. `first_any_SS` records an affirmative constituent classification. `clean_regular_before` counts completed eligible routine opportunities before that detection. `first_any_days` is elapsed calendar time from the anchor. Schedule fields have the meanings above. Ambiguous first detections are never bypassed to select a subsequent clearer record.

## Generated pathway fields

`event_k` is the opportunity of a first eligible repeat, where observed. `rec_ss`, `rec_n`, and `rec_issue` describe the repeat bundle. `first_clear` identifies an observed nonciting first opportunity. `first_per_mine` selects the earliest eligible index episode at each mine without conditioning on later recurrence. `period` uses index inspection start year. An event within horizon K is `event_k <= K`; a completed nonciting sequence has at least K observed opportunities and no event within K. All other cases are primary-pathway exits, with recorded reasons preserved.

## Interpretation limits

S&S values are those retained in the supplied administrative snapshot. Revision histories and point-in-time original assessments are not reconstructed. The source does not establish constant operation, equivalent detection, physical defect identity, remedial-action quality, or realized injury from a provision-matched citation. Neither an interrupted path nor no available later record is a successful compliance outcome.


## Composition outputs

- `composition_by_opportunity.csv`: `k` is the eligible opportunity (1–4), `attribute` is a recorded index characteristic, `n` is the observed denominator, `count` is the number with the characteristic, and `fraction=count/n`.
- `standardization_cells.csv`: four opportunities crossed with 16 strata. `observed` and `repeats` are cell counts; `reference_weight` is the first-opportunity stratum share; `fraction` is the observed within-cell citation fraction. `part`, `index_ss`, and `period` define the strata.
- `standardized_observed_fractions.csv`: unstandardized and common-mix fractions with pointwise percentile intervals. Weights are recalculated in each mine resample.
- Regulatory part is not a direct measurement of mine size, production, or geology. `raw_n >= 3` in Table S6 is a descriptive index-count category, not a validated prioritization threshold.
