## Concern: security
- Every entry point (HTTP, CLI, queue, webhook, file): who may call it, and where is that
  checked — with a test that a caller without the right gets refused?
- Input parsed and validated once at the boundary; no injection into SQL, shell, templates,
  paths, URLs.
- Secrets: not in the repo, not in logs, not in error messages; personal data minimised.
- Sessions, passwords, tokens: storage, expiry, rotation, comparison in constant time.
- Dependencies with known vulnerabilities; outbound calls to hosts taken from input.
