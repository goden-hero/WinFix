# Safe Windows VM Demonstration Guide: Windows Explorer / Taskbar Crash Recovery

> [!IMPORTANT]
> **Safety Notice**: WinFix Agent does **NOT** contain any functionality to automatically or intentionally terminate, crash, or kill `explorer.exe` or any other process. The procedure below is for manually testing and demonstrating WinFix's crash recovery capabilities inside a disposable Windows test Virtual Machine (VM).

---

## Controlled VM Demonstration Procedure

Follow these steps to demonstrate WinFix Agent diagnosing and safely recovering an Explorer / taskbar crash:

### Step 1: Prepare Disposable Test Environment
1. Start your disposable Windows Virtual Machine (VM).
2. Take a VM snapshot prior to testing.

### Step 2: Manually Simulate Explorer Crash
1. Open Windows Task Manager by pressing `Ctrl + Shift + Esc`.
2. Locate **Windows Explorer** (`explorer.exe`) under the **Processes** tab.
3. Right-click **Windows Explorer** and select **End task**.
4. Observe that the Windows taskbar, Start menu, and desktop icons disappear.

### Step 3: Run WinFix Agent Diagnosis
1. Launch WinFix Agent (or open the WinFix web application).
2. In the problem prompt, enter:
   > *"My taskbar and desktop icons disappeared. Please diagnose the issue."*
3. Click **Diagnose Problem**.
4. Verify that WinFix Agent detects `explorer.exe` is **NOT running** (`running: false`, impact: `likely_affected`).

### Step 4: Review and Approve Recovery Plan
1. Review the generated repair plan step:
   - **Action**: Restart Windows Explorer
   - **Target**: `explorer.exe`
   - **Scope**: Windows Explorer shell process
   - **Risk Level**: MEDIUM RISK
2. Click **Approve Step** to explicitly authorize execution.

### Step 5: Execute and Verify Recovery
1. Click **Execute Approved Remediation**. WinFix launches the fixed executable `explorer.exe`.
2. Click **Verify System State**.
3. Confirm that WinFix independently queries system processes, confirms `explorer.exe` is running, and reports:
   > *"Independent verification confirmed Windows Explorer (explorer.exe) is running. The taskbar and desktop shell may have recovered."*
4. Observe that the Windows taskbar, Start menu, and desktop icons reappear.

---

## Manual Fallback Procedure (Emergency Recovery)

If WinFix Agent or Task Manager is closed and the desktop remains blank, restore Explorer manually:

1. Open Task Manager: `Ctrl + Shift + Esc`.
2. Click **Run new task** (or `File` -> `Run new task`).
3. Type: `explorer.exe`
4. Press `Enter`.
