"""Compatibility entrypoint for the current proof-kernel sweep.

The old surface runner used the pre-frontier ``state_recurrence`` API. The
current acceptance path is ``viability_search.py``.
"""

from viability_search import main


if __name__ == "__main__":
    main()
