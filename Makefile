.PHONY: setup build compatibility test unit fuzz invariants check security probes
# Devnode suites share a staged workspace; even `make -j check` must serialize them.
.NOTPARALLEL:
SEED ?= 20260920
FUZZ_CASES ?= 100
STEPS ?= 30
setup:
	python3 scripts/bootstrap.py
build:
	python3 scripts/generate_multitoken.py
	./scripts/leo build --path pwn_loan_poc --offline
compatibility: build
	python3 scripts/check_multitoken_compatibility.py
unit:
	python3 -m unittest discover -s tests -v
fuzz:
	python3 scripts/multitoken_fuzz.py --seed $(SEED) --cases $(FUZZ_CASES)
invariants: build
	python3 scripts/multitoken_integration.py --invariants-only --seed $(SEED) --steps $(STEPS)
check: unit compatibility fuzz test invariants security
test: build unit
	python3 scripts/multitoken_integration.py
security: build
	python3 scripts/multitoken_integration.py --security-only
probes:
	./scripts/leo build --path custody_probe --offline
	./scripts/leo build --path usdcx_composition_probe --offline
	./scripts/leo build --path artifacts/token-dispatch-probe --offline
