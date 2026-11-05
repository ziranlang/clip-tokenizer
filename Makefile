.DEFAULT_GOAL := check
ZIRAN ?= ../../ziran/build/bin/ziran
.PHONY: check
# Invoke through build-queue; direct canonical paths need no clone or fetch.
check:
	sh tests/check.sh $(ZIRAN)
