# Amazon Redshift Query Performance Runbook

## Purpose

Investigate slow Redshift queries and query-plan regressions.

## Signals

Inspect query history, query IDs, execution and queue time, execution plans, scan volume, join behavior, rows processed, disk-based steps and spill metrics. Compare the incident window with a known healthy period.

## Investigation steps

1. Identify affected query IDs and workload groups.
2. Compare EXPLAIN plans and query text/revisions where available.
3. Check scan volume, joins, predicates, data skew and statistics freshness.
4. Separate queue wait from execution time.
5. Correlate the query behavior with WLM changes, data changes, maintenance, or workload growth.
6. Check whether spill or cluster capacity is a contributing factor.

## Evidence standard

A slow query is not automatically the root cause. Build a trigger-to-mechanism-to-impact chain and retain competing explanations when evidence is incomplete.
