"""Compatibility wrapper for the current proof-kernel state recurrence.

The active implementation lives in ``entry_state.py``. This file remains so
older local commands that imported ``state_recurrence`` fail less abruptly.
"""

from entry_state import (
    EntryKey,
    EntryState,
    PassLedgerRow,
    initial_raw_state,
    run_pass,
    run_profile,
    run_scheduled_profile,
)

__all__ = [
    "EntryKey",
    "EntryState",
    "PassLedgerRow",
    "initial_raw_state",
    "run_pass",
    "run_profile",
    "run_scheduled_profile",
]
