# Counted streams: unique match and hashed side (2026-11-27)

Pull request: https://github.com/IBSurgeon/hqbird/pull/84 (branch `v5.0-impr-opt-counted-side`, base `v5.0-impr-opt`).
Optimizer notes 4.67 and 4.68. Tests: `../../tests/79_hash_agg_counted_join.sql`, `../../tests/91_counted_unique_and_side.sql`.

## Files

- `run_suite.py <engine_dir> <work_dir> <out_dir> [first [last]]` - runs every `NN_*.sql` test of all review
  folders with the embedded isql of one engine folder. It writes the test aliases (with their settings) into
  `databases.conf` of the engine folder and deletes the database files a test creates.
- `cmp.py <out_a> <out_b> [lines]` - compares two output folders test by test (times and statistics lines removed).
- `suite_base.log`, `suite_new.log` - the return codes of the two runs. The same 6 tests fail on both builds:
  18, 19, 20, 45, 54 (known) and 88.
- `mk_timing.sql` - the timing database (t 60 000, dim 2 000, fact 2 000 000 rows).
- `timing.py` - the 14 timing queries; `timing2.py <db> <rounds> name=engine_dir,...` runs the builds in turn and
  prints the best time.

## Notes

- 14 tests with sampled statistics (03, 05, 10-14, 16, 25-28, 33, 48) differ in the row estimates between two
  runs of the same build. Compare them with a second run of the base build, not with the change.
- The timings were taken on a machine loaded by other jobs: run the builds in turn and take the best time.
