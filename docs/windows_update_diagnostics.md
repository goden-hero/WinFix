# Windows Update Diagnostics (Stage 1)

WinFix Agent provides safe, controlled, read-only diagnostics for Windows Update health and readiness following the workflow:

`Detect → Diagnose → Plan → Approve → Fix → Verify`

---

## Technical Overview & Scopes

Stage 1 is **strictly read-only**. It inspects system state using narrow, deterministic adapters without making any modifications, running scripts, or attempting premature remediation.

### 1. Operating System Compatibility
- **Platform Detection**: Validates whether execution is occurring on native Windows (`platform.system() == "Windows"` and `os.name == "nt"`).
- **Non-Windows Safety**: On non-Windows platforms (e.g., Linux, macOS, CI environments), all checks cleanly return `NOT_APPLICABLE` structured evidence without throwing exceptions or attempting Windows-only calls.

---

### 2. Core Service Status Inspection
Inspects the following fixed Windows services:
- `wuauserv` — Windows Update Service
- `BITS` — Background Intelligent Transfer Service
- `CryptSvc` — Cryptographic Services

**Collected Metadata**:
- `name`: Fixed service identifier.
- `display_name`: Human-readable service name.
- `status`: Current service state (`running`, `stopped`, `disabled`, `missing`, `unavailable`).
- `startup_type`: Service startup configuration (`automatic`, `manual`, `disabled`, `boot_system`, `unknown`).
- `is_running`: Boolean flag indicating active execution.
- `error`: Safe string error message if inspection fails.

> [!NOTE]
> Service names are fixed API constants. Service names supplied by the LLM or user payloads are strictly rejected.

---

### 3. Pending Reboot Indicators
Inspects read-only Windows registry keys for pending reboot flags that could block Windows Update installations:
- `SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending`
- `SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired`
- `SYSTEM\CurrentControlSet\Control\Session Manager` -> `PendingFileRenameOperations`

**Possible States**:
- `REBOOT_PENDING`: One or more pending reboot indicators exist.
- `NO_REBOOT_PENDING`: Registry keys checked contain no reboot indicators.
- `UNKNOWN`: Returned when registry access is restricted, permission fails, or reads are inconclusive.

---

### 4. Download Cache Metadata
Inspects the fixed Windows Update download directory:
`%SystemRoot%\SoftwareDistribution\Download`

**Collected Metadata**:
- `cache_exists`: Whether the directory is present.
- `cache_accessible`: Whether the directory can be safely read.
- `cache_size_bytes`: Total byte size of cached patch downloads.
- `file_count`: Total count of files in the download cache.
- `error_message`: Detailed permission or access failure error if applicable.

---

## Strict Read-Only Guarantees

Stage 1 guarantees:
- **No System Mutation**: No services are started, stopped, modified, enabled, or disabled.
- **No Registry Edits**: Registry keys are opened in read-only mode (`KEY_READ`). No keys or values are created or changed.
- **No File Deletions**: No files or directories are renamed, modified, or deleted.
- **No Shell Execution**: No generic PowerShell, CMD, or arbitrary command execution occurs.
- **No Unrestricted Execution**: The LLM cannot specify custom commands, arguments, registry paths, or service targets.

---

## Diagnostic Limitations & Interpretation

1. **Supporting Evidence vs. Root Cause**: A stopped service or large cache size is supporting evidence, not absolute proof of component corruption.
2. **Cache Size Semantics**: A large download cache directory indicates pending or past update downloads; it does not prove cache corruption.
3. **Meaning of UNKNOWN**: An `UNKNOWN` reboot status indicates incomplete registry read visibility (e.g., non-admin execution context), not necessarily a system error.
4. **Future Remediation Requirements**: Any future remediation action (e.g., service restart, cache cleanup) requires separate implementation, validator policies, risk assessments, user approval flows, and independent verifiers.
