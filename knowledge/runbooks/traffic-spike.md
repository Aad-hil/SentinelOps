# Redshift Workload Growth Runbook

For workload growth or concurrency pressure, compare query arrival rate, workload-group mix, WLM queue wait, queued query count, concurrency, query runtime, and compute utilization. Identify whether demand growth, a WLM configuration change, inefficient SQL, or cluster capacity is the primary driver.

Traffic growth is not automatically a root cause. Distinguish WLM contention (RSH1), query-plan regression (RSH2), and compute capacity pressure (RSH3) using workload and query-level evidence. If evidence does not discriminate, retain RSH12.
