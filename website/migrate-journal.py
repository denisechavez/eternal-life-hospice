#!/usr/bin/env python3
"""Idempotent, additive Journal schema setup before an approved publication."""
from journal_release import initialize
from journal_owner_approval import apply as apply_owner_approval

initialize()
apply_owner_approval()
print("Journal approval storage ready")
