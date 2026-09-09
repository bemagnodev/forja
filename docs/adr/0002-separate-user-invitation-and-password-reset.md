---
status: accepted
date: 2026-09-09
---

# 2. Separate user invitation and password reset commands

## Context
Previously, the management command `invite_user` handled both creating new users and updating existing users' handles while issuing password links. Furthermore, invited users were created with `is_active=True`, allowing potential premature access, and passwords had only a trivial length check (>= 6 chars) without enforcing complexity.

## Decision
1. **Separate Commands:**
   - `invite_user`: Strictly creates new pending users (`is_active=False`, unusable password). If the username already exists, it fails with a `CommandError` directing the admin to use `reset_user_password`.
   - `reset_user_password`: Specifically targets existing users, generating a password reset link without modifying user attributes, handles, or current password until the link is consumed.
2. **Activation on Acceptance:**
   - When a valid invitation token is accepted via `POST /api/auth/set-password`, the user is set to `is_active=True` inside a database transaction (`select_for_update`).
3. **Simple Password Policy:**
   - Enforced via Django's password validation infrastructure (`SimpleComplexityPasswordValidator` in `api.password_validation`): minimum 8 characters, at least one letter, at least one digit, and at least one special character (excluding space).
4. **Link Expiration:**
   - Set to 3 days (`PASSWORD_RESET_TIMEOUT = 60 * 60 * 24 * 3`).
5. **Frontend Base URL:**
   - Sourced from `settings.FRONTEND_URL` by default, with `--base_url` CLI option continuing to take precedence.

## Benefits
- Clear single-responsibility boundaries for administrative operations.
- Security against inactive/unconfirmed users logging in or tampering with existing accounts.
- Granular, secure transactional password setting and deterministic token invalidation.

## Consequences & Alternatives Considered
- Discarded maintaining a combined command because it obscured intent and risked unintentionally resetting active member accounts.
- Discarded complex password policies (e.g., uppercase/lowercase or dictionary similarity checks) to minimize friction for team members while retaining solid baseline entropy.
