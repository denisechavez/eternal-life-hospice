#!/usr/bin/env python3
"""Idempotent, additive Journal schema setup before an approved publication."""
from journal_release import initialize
from journal_owner_approval import apply as apply_owner_approval, apply_october
from form_antispam import initialize as initialize_intake_security

initialize()
initialize_intake_security()
apply_owner_approval()
apply_october()
print("Journal approval storage ready")
