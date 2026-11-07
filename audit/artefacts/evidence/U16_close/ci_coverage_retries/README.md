# CI coverage lane: files over the 240 s per-file limit, absorbed by the retry

`ci_retry_history.md` lists, per CI job of four pushes (8d44fd1, 2949ed9, cbb65df, 1cff5a2), every "exceeded 240s",
"root-cause item" and "Passed only on retry" line with the job's file counts and step wall time. The four
`cov_job_<id>.log.gz` are the unit-tests-coverage logs' last 5000 lines (the log tool's cap; the setup head with the
parallelism line is cut). `ci_durations.py` computes per-file wall time from a log. Only the coverage lane retried:
three files at 2949ed9, none at cbb65df, five at 1cff5a2; every non-coverage job, zero. Recorded as OF-68.
