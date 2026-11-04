# Configuration and secrets

How @@NAME@@ handles settings that must not be public.

- Real values live in `.env` (or the operating system's credential store). They are never committed, logged or copied into documents.
- `.env.example` lists every setting by **name** with a placeholder value, so anyone can see what is needed.
- Code reads settings from the environment; it never contains a key, token or password.
- If a secret is ever committed, treat it as leaked: revoke and replace it, then clean the history deliberately with the owner's approval.

TO CONFIRM: the list of settings this project needs (names only).
