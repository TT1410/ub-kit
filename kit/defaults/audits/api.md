## Concern: the API
- The contract (OpenAPI, protobuf, types, docs) and the code: do they agree, and does a test
  check that they do?
- Errors: stable codes and shapes, no internals leaked, the same error for the same fault.
- Paging, limits, filtering and sorting on every list; time zones, money and rounding at the
  boundary.
- Backward compatibility: what a client written against the last release would break on.
- Idempotency keys on writes a client may retry.
