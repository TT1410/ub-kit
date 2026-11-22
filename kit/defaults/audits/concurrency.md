## Concern: races and concurrency
- Every place two things can run at once: requests, workers, jobs, retries, timers, webhooks.
  Which shared state do they touch, and who is the one writer?
- Retries and redeliveries: is every operation idempotent (a unique key, a state check) so a
  duplicate does not write twice?
- Transactions and locks: isolation levels, check-then-act gaps, ordering assumptions.
- Is there a test that would catch a race? Martin's way: jitter tests — insert random delays at
  the critical points and run the suite many times. Name where such a test is missing.
