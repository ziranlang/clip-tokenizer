.DEFAULT_GOAL := check
# The locked toolchain, fetched and built on first use, or the checkout an
# ignored ziran.local.toml names; ZIRAN=path/to/ziran replaces both.
LOCK_FLAGS := $(if $(wildcard ziran.local.toml),,--locked)
.PHONY: check
# Invoke through build-queue.
check:
	$(if $(ZIRAN),,$(if $(wildcard ziran.local.toml),,ziran fetch --locked))
	sh tests/check.sh "$(or $(ZIRAN),$$(ziran pkg path ziran $(LOCK_FLAGS))/build/bin/ziran)"
