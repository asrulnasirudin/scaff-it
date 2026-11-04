# @@NAME@@: project specification

Created @@DATE@@. This is the source of truth for **what** we are building.
Entries marked **TO CONFIRM** were not established during setup; the owner fills them in. Nothing here is a decision unless it says so.

## 1. Project identity
- Name: @@NAME@@ (`@@SLUG@@`)
- Category: @@CATEGORY@@

## 2. Product description
@@DESCRIPTION_BLOCK@@

## 3. Target users
TO CONFIRM

## 4. Problem being solved
TO CONFIRM

## 5. Goals
TO CONFIRM

## 6. Non-goals
TO CONFIRM

## 7. Functional requirements
TO CONFIRM

## 8. Target platform
@@PLATFORMS_BLOCK@@

## 9. Host application
@@TARGETS_BLOCK@@

## 10. Technology stack
@@STACK_BLOCK@@

## 11. Architecture requirements
TO CONFIRM

## 12. Dependencies and toolchain
@@TOOLCHAIN_BLOCK@@

## 13. Security requirements
Baseline set during setup (extend as needed):
- Secrets (keys, tokens, passwords) never enter the repository, public or private. Use `.env`, kept out of Git; `.env.example` holds placeholders only.
- Local-only material: @@LOCAL_ONLY@@
- Files named @@WATCH@@ are flagged for review, not ignored.
TO CONFIRM: any additional requirements (authentication, data privacy, licences).

## 14. Testing requirements
Checklist: `@@QA_PATH@@`.
TO CONFIRM: what must be tested automatically and what by hand.

## 15. Distribution requirements
@@DISTRIBUTION_BLOCK@@

## 16. Open questions
@@QUESTIONS@@
