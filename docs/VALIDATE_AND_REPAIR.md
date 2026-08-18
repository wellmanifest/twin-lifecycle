# Validate, then repair, one stage at a time

```dsl
DOCUMENT TWIN_VALIDATE_AND_REPAIR
VERSION 1
LANGUAGE EN
MODE STRICT
SCHEMA "wellmanifest.twin-lifecycle/v1"
BLUEPRINT "../standard/blueprint.validate-repair.json"
COMPOSES "wellmanifest/repair-lifecycle"
```

This is the standard for **how** a Digital Twin is validated and then
repaired. The reference `twin-reference/v1` graph still owns product birth
through retirement. `service-observe-repair/v1` owns the operating loop of a
**service twin**: observe the live account, store a secret-free inventory,
bind one target, preflight, dry-run, evaluate an exact grant, then verify the
effect. Mutation authority stays in `wellmanifest/repair-lifecycle`.

A lifecycle document records that declared criteria were evaluated. It never
grants apply, never stores a password or token, and never treats a score or
model verdict as evidence.

## Sequential rule

Forward progress is adjacent. The only legal non-feedback, non-terminal
advances are the next declared stage. Skip-ahead is rejected as
`TWINLC-SEQUENCE-001` on the blueprint and `TWINLC-TRANSITION-001` on a
request. Feedback is allowed only into a `repeatable` earlier stage when
currency was lost.

```text
observed
  → inventoried
  → target-bound
  → preflighted
  → planned
  → granted
  → verified
       ↺ inventoried   (next target)
target-bound ↺ inventoried   (stale inventory)
planned      ↺ target-bound  (binding or plan hash changed)
granted      ↺ planned       (grant superseded)
any bound stage → abandoned
```

No earlier fact implies a later one. A complete inventory does not bind a
target. A healthy binding does not pass preflight. A green dry-run does not
evaluate a grant. An evaluated grant is not apply authority. Apply, if it
happens, is a separately authorized repair whose exact candidate this
lifecycle later verifies.

## What the twin must store

Enough secret-free state to choose and check a target **without** asking
knowledge for “the only allowed domain”:

| Field | Purpose |
| --- | --- |
| `account_id` | one login / API / SSH account |
| `subscriptions[]` | every webspace that login can see |
| `domains[]` | domains and roles under each subscription |
| `docroot` | exact publish path for that domain |
| `vault_entry_id` / `vault_refs` | pointers only |

The twin MUST refuse a target that is not in inventory. The twin MUST NOT
infer a second domain from a repository path when inventory has no row.

## Worked example: Plesk service twin

Plesk is one account with many subscriptions. Treating a healthy
`plesk_subscription` or a single `PLESK_TARGET_DOMAIN` as the whole account
was a lifecycle error, not an API limit.

| Stage | Plesk evidence | Forbidden shortcut |
| --- | --- | --- |
| `observed` | `plesk://host/account/query/subscriptions` or snapshot without a filter | One env domain stands for the account |
| `inventoried` | `digitaltwin-run/plesk-service-twin/inventory/account-subscriptions.json` | Password or API token in the twin file |
| `target-bound` | one `subscription_name` + domain + docroot + `plesk-sftp-…` | Reuse subscription A credentials on domain B |
| `preflighted` | source completeness, `plesk_default_page_shadowing` absent | Skip because the last publish “looked fine” |
| `planned` | dry-run receipt whose `input_hash` / `plan_hash` matches this binding | Replay an old plan after the docroot changed |
| `granted` | gate evaluated for that exact hash (`authorityGranted: false`) | Chat approval or a stale form |
| `verified` | independent GET of `/` is the application, not the Plesk default page | Merge or apply receipt as proof of effect |

Normative companions: `knowledge://subactor/architecture.deployment-binding/v12`
and `wellmanifest/repair-lifecycle` §§1–6. Knowledge is not a substitute for
the inventory snapshot.

## How to repair, in order

1. Observe the account. Refresh inventory. Stop if the snapshot is estimated
   and a live observe URI exists.
2. Bind **one** target from inventory. If the desired domain is missing, stay
   in `inventoried` or abandon. Do not invent a docroot.
3. Preflight that binding only.
4. Dry-run. Keep the returned plan hash. A changed binding invalidates it
   (`rebind-target` then `plan` again).
5. Evaluate the grant against that hash. This standard still asserts
   `approvalGrantsAuthority: false`. Apply uses repair-lifecycle authority.
6. After an authorized apply (outside this graph), `verify-effect` from
   independent observation. If the effect is absent, do not mark verified.
7. For the next service, `next-target` returns to `inventoried`. Do not jump
   to `planned`.

Replay of `lifecycle-state` does not advance a stage and does not execute
apply.

## Binding a service twin

1. Pin `standard/blueprint.validate-repair.json` as a contract source the same
   way `docs/TWIN_BINDING.md` pins the schema.
2. Set `$.lifecycle.blueprintRef` to `service-observe-repair` / `v1` and the
   canonical digest of that file.
3. Map inventory and dry-run receipts to `evidence://…/rN`. Never put a
   secret in an evidence URI.
4. Keep `twin-reference/v1` for the product twin of the standard itself.
