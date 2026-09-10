# WinFix Agent Safety Model

## Non-negotiable boundary

```text
LLM recommendation -> Pydantic validation -> registry lookup -> risk policy -> explicit approval -> controlled executor -> Windows capability
```

The LLM has no endpoint or tool for arbitrary PowerShell, CMD, registry writes, file deletion, process termination, or direct WinUtil access. It may recommend only `ActionId` values defined in code.

## Risk policy

| Risk | Examples | Policy |
| --- | --- | --- |
| Low | Diagnostics, reads, evidence collection | May run automatically. |
| Medium | Startup disable, bounded temp cleanup, allowlisted app removal, privacy profiles, SFC/DISM | Always needs explicit approval. |
| High | Driver removal, boot changes, security disabling, arbitrary registry/files | Blocked for this MVP. |

## Enforcement rules

1. `ActionRegistry` owns every action ID, parameter schema, executor function name, verifier function name, risk, and approval requirement.
2. `ActionValidator` rejects unknown IDs and parameters not declared by the registry.
3. `SafetyPolicy` blocks high-risk actions even if a client claims approval.
4. `ControlledExecutor.execute()` accepts `RecommendedAction`, never a command string.
5. WinUtil, when added, is called only by a registry-backed adapter after validation.
6. Each mutation must capture before state and supply a deterministic verification metric.

## Current execution status

The registry describes the intended MVP actions, but the default adapter reports `not_implemented` and changes nothing. Before enabling a real Windows action, implement its fixed backend capability, parameter allowlist, elevation/permission behavior, before/after verifier, automated tests, and rollback or user-visible failure behavior.

## Threat assumptions

Treat model output, client payloads, discovered process names, registry values, and WinUtil output as untrusted data. Log structured action IDs and outcomes, but never execute strings from those sources. UI approval is necessary but not sufficient; backend policy remains authoritative.
