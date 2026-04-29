# Firms Directory

Each subdirectory corresponds to a **deployment configuration**.

## Structure

```
firms/
  _default/             ← Fallback for all configs (always loaded)
    config.json         ← Tier limits, features
    branding.json       ← Logo, colors, fonts
    prompt_override.md  ← Appends to SPECTR_SYSTEM_PROMPT
    disclaimer.md       ← Footer text on generated docs

  algorythm/            ← Internal deployment (algorythm.spectr.in)
    config.json
    branding.json
    prompt_override.md

  cam/                  ← Dedicated CAM deployment (cymllp.spectr.in)
    config.json
    branding.json        ← CAM logo, CAM colors
    prompt_override.md   ← CAM's drafting style, citation conventions
    playbook_overrides.py  ← CAM's NDA/SPA templates
```

## How it loads

`config_loader.py` reads `FIRM_SHORT` env var at startup:

- `FIRM_SHORT=""` → runs as **spectr.in** (multi-tenant SaaS, shared DB)
- `FIRM_SHORT="cam"` → runs as **cymllp.spectr.in** (dedicated CAM instance, own DB)

For every config lookup, falls back: `firms/<firm>/` → `firms/_default/` → hardcoded.

## Adding a new firm

Run `./scripts/new-firm.sh <shortname> "<Firm Full Name>"`. Script creates:

- `firms/<shortname>/config.json` (from template)
- Fly.io app `<shortname>-spectr`
- MongoDB Atlas cluster
- Subdomain `<shortname>.spectr.in`
- OAuth client

After creation, edit `firms/<shortname>/prompt_override.md` + `branding.json` to customize for that firm.

## Per-firm isolation

- **DB-level:** Each dedicated deployment has its own MongoDB — data never shared.
- **Token-level:** Each user's OAuth tokens are stored in their firm's DB only.
- **Request-level:** `config_loader.tenant_filter(user_id)` is applied to every Mongo query.
