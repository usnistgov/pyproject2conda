# interface to pre-commit prettier
pre-commit run prettier --files $@ &> /dev/null || true
