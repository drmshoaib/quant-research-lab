# Research Note: Cross-Sectional Signal Discovery

**Status:** Development / Hold-out locked  
**Author:** Muhammad Shoaib

## 1. Question and motivation
State the hypothesis before discussing results.

## 2. Data
Document provider, universe, date range, missingness, filters and known biases.

## 3. Timing and leakage controls
Specify exactly when every feature is known, when positions can be entered, and how labels are formed.

## 4. Features
List the frozen feature set and economic/statistical rationale. Do not add features after seeing hold-out performance.

## 5. Models
Describe Ridge baseline and nonlinear comparator, including all fixed hyperparameters.

## 6. Validation
Describe expanding-window purged validation and the untouched final hold-out.

## 7. Signal results
Report fold-by-fold and aggregate rank IC, HAC uncertainty, stability by time period, and failure cases.

## 8. Portfolio translation
Explain dollar neutrality, gross/name constraints, turnover and costs. Separate signal quality from portfolio engineering.

## 9. Robustness checks
Include cost sensitivity, feature ablations, alternative horizons, regime analysis and bootstrap intervals. Clearly distinguish pre-specified checks from exploratory ones.

## 10. Final hold-out
Complete this section once, only after the protocol is frozen.

## 11. What failed
Record hypotheses and variants that did not survive out-of-sample testing.

## 12. Conclusions
State what the evidence supports, what it does not support, and the next justified experiment.
