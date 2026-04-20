# uvm_pygen/constants/config_aliases.py

"""Accepted YAML key aliases for environment and other top-level blocks.

Single source of truth — imported by ConfigResolver (for unified-file
detection) and UVMConfiguration._parse() (for flexible key lookup).
"""

ENV_BLOCK_ALIASES: frozenset[str] = frozenset({"environment", "env", "uvm_env"})
TRANSACTION_ALIASES: frozenset[str] = frozenset({"transactions", "transaction", "trans", "uvm_transactions"})
PARAMETER_ALIASES: frozenset[str] = frozenset({"parameters", "parameter", "params", "param", "uvm_parameters"})
ENUM_ALIASES: frozenset[str] = frozenset({"enums", "enum", "enumerations", "enumeration", "uvm_enums"})


# Maps each canonical yaml_key to its full alias group (canonical included).
# ConfigLayout uses this to expand uvm_keys/dut_keys and build required-key groups.
YAML_KEY_ALIAS_GROUPS: dict[str, frozenset[str]] = {
    "environment": ENV_BLOCK_ALIASES,
    "transactions": TRANSACTION_ALIASES,
    "parameters": PARAMETER_ALIASES,
    "enums": ENUM_ALIASES,
}
