# Isolated environment for running a project's test suite.
# Run with --network none, a memory cap, and a non-root user (all
# enforced by the `docker run` flags in app/sandbox.py, not just here).
FROM python:3.11-slim

RUN useradd -m -u 1000 sandboxuser
WORKDIR /app
COPY sandbox_entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
USER sandboxuser

ENTRYPOINT ["/entrypoint.sh"]
