---
name: rms-jenkins-buildler
description: |
  Execute Jenkins build tasks for iOS/Android apps, monitor build status, and retrieve logs.
  Supports single-task concurrency control with automatic running task detection.
  Use when user mentions: build, package, deploy, trigger Jenkins, check build status, view logs,
  stop/abort a build, or rerun a previous build.
  Supports: triggering builds, querying status, retrieving console logs, stopping builds.
---

# RMS Jenkins Buildler Skill

Execute and monitor Jenkins build pipelines for mobile apps (iOS & Android) with single-task concurrency control.

## Core Features

1. **Single-Task Concurrency Control** - Only one build task can run at a time
2. **Automatic Running Task Detection** - Before triggering any new build, checks for running tasks
3. **Smart Parameter Inference** - Automatically sets platform and environment based on upload target
4. **Mandatory Parameter Confirmation** - platform and environment must be explicitly specified
5. **Log File Delivery** - Logs are always returned as file attachments for IM platforms

## When NOT to Use

- User asks for general CI/CD advice or Jenkins configuration help
- User wants to modify Jenkins job configurations
- User asks about code review, testing, or deployment to environments other than Jenkins
- User asks about non-Jenkins build systems

## Core Commands

All Jenkins operations MUST go through `jenkins.py`. Never use raw curl.

```
{script_path} = {skill_dir}/scripts/jenkins.py
```

| Command | Description |
|---------|-------------|
| `trigger <job> <platform> <env> <flutter> <ios> [android] [isDebug] [upload] [version] [updateNotes] [submitForReview] [needPullBranch` | Trigger a new build |
| `rerun <job> <build_num>` | Rerun a specific build (reuse parameters) |
| `rerun-last <job>` | Rerun the last build |
| `stop <job> <build_num>` | Stop a specific build |
| `stop-running [job]...` | Stop all running builds |
| `status [job]...` | Check build status |
| `running [job]...` | Check if any build is running |
| `last <job>` | Get last build info |
| `info <job> <build_num>` | Get detailed build info |
| `log-tail <job> <build_num> [n]` | Get last N lines of console log (default: logTailLines from config) |
| `full-log <job> <build_num>` | Get full console log |

## Input / Output

```yaml
Input:
  - job: string              # Jenkins job name (uses DEFAULT_JOB if not specified)
  - command: string          # One of: trigger, rerun, rerun-last, stop, stop-running,
                             #   status, running, last, info, log-tail, full-log
  - platform: string         # iOS | Android | all (REQUIRED)
  - environment: string      # test | test_old | product | product_old | develop | gray | preproduct (REQUIRED)
  - flutterBranch?: string   # Flutter module branch (default: master)
  - iosBranch?: string       # iOS native branch (default: master)
  - androidBranch?: string   # Android native branch (default: master)
  - isDebug?: boolean        # Android debug build (default: false)
  - uploadTarget?: string    # pgyer | appleAppStore (default: pgyer)
  - build_num?: number       # For rerun/stop/info commands

Output:
  - success: boolean
  - build_num?: number       # Returned after successful trigger
  - message: string          # Human-readable status or result
  - errors?: string[]        # Error details if success=false
```

## Parameter Defaults

| Parameter | Default | Notes |
|-----------|---------|-------|
| `platform` | `iOS` | iOS / Android / all |
| `environment` | `test` | test / test_old / product / product_old / develop / gray / preproduct |
| `flutterBranch` | `master` | Flutter module branch |
| `iosBranch` | `master` | iOS native branch |
| `androidBranch` | `master` | Android native branch |
| `isDebug` | `false` | Android only |
| `uploadTarget` | `pgyer` | pgyer / appleAppStore |
| `needPullBranch` | `true` | Whether to pull remote branch code |
| `logTailLines` | `500` | Default log lines for log-tail command |

## Smart Parameter Rules

These rules are automatically applied when triggering builds:

| Condition | Action |
|-----------|--------|
| `uploadTarget=appleAppStore` | Auto-set `platform=iOS`, `environment=product` |
| `submitForReview=true` | Auto-set `platform=iOS`, `environment=product`, `uploadTarget=appleAppStore` |

## Validation Rules

| Rule | Behavior |
|------|----------|
| `platform` not specified | Reject - platform is required |
| `environment` not specified | Reject - environment is required |
| Android + develop/gray/test_old/product_old | Auto-downgrade to test, notify user |
| uploadTarget=appleAppStore + Android | Reject - Android not supported |
| uploadTarget=appleAppStore + environment≠product | Auto-correct to product |
| isDebug=true + platform=iOS | Reject - iOS not supported |

## Concurrency Control

### Running Task Detection

Before triggering ANY new build (including rerun), the system checks for running tasks:

1. If running task found → Display build_num and business parameters (platform, environment, uploadTarget, submitForReview, flutterModuleBranch, iOSNativeBranch, androidNativeBranch, version, updateNotes, isDebug, needPullBranch)
2. Ask user to confirm if they want to continue (will terminate running task)
3. Only proceed with new task after user confirmation

### Output Format for Running Tasks

```
发现有任务正在运行:
  任务: my-jenkins-job
  构建号: #123
  参数:
    platform: iOS
    environment: test
    uploadTarget: pgyer
    submitForReview: false
    flutterModuleBranch: master
    iOSNativeBranch: developer
    androidNativeBranch: master
    version:
    updateNotes:
    isDebug: false
    needPullBranch: false

继续新任务将终止当前任务，是否继续？
```

## Trigger Flow

### Step 1: Check for Running Tasks

```bash
python3 jenkins.py running <job>
```

- If running → Show confirmation dialog with running task details
- If not running → Proceed to parameter validation

### Step 2: Parameter Validation

- Validate `platform` and `environment` are provided
- Apply smart parameter rules
- Check for invalid combinations

### Step 3: Execute Trigger

```bash
python3 jenkins.py trigger <job> <platform> <env> <flutter> <ios> [android] [isDebug] [upload] [version] [updateNotes] [submitForReview] [needPullBranch]
```

### Step 4: Return Results

After successful trigger, immediately return:

```
✅ 已触发 my-jenkins-job #124

📦 构建参数：
  platform: iOS
  environment: test
  uploadTarget: pgyer
  submitForReview: false
  flutterModuleBranch: master
  iOSNativeBranch: developer
  androidNativeBranch: master
  version:
  updateNotes:
  isDebug: false
  needPullBranch: true
```

## Build Info Output Format

When displaying `info` results, follow this order:

1. **Basic info**: build number, result, trigger time, duration
2. **Status details**: For FAILURE/ABORTED/NOT_BUILT, show reason
3. **Key parameters**: platform, environment, uploadTarget, submitForReview, flutterModuleBranch, iOSNativeBranch, androidNativeBranch, version, updateNotes, isDebug, needPullBranch
4. **Upload results**: pgyer or App Store Connect info (if applicable)

## Log Retrieval

- `log-tail` → writes last N lines to file, returns **absolute file path**
- `full-log` → writes complete log to file, returns **absolute file path**

**Default behavior for IM platforms:**
- Always return logs as file attachments
- `log-tail` uses `logTailLines` from config.json (default: 500)
- User can override by specifying line count: `log-tail <job> <build_num> 1000`

**File delivery flow:**
1. Script writes log to file, returns absolute path
2. Agent sends file via `openclaw message send --media <path> --channel <current_platform>`
3. Current platform determined by session channel: feishu / wechat / other

## Status Output

Status is displayed with clear icons and descriptions:

| Status | Icon | Description |
|--------|------|-------------|
| SUCCESS | ✅ | 构建成功 |
| FAILURE | ❌ | 构建失败 |
| ABORTED | ■ | 已终止 |
| RUNNING | 🔄 | 运行中 |
| NOT_BUILT | ⚠️ | 未构建 |

For FAILURE/ABORTED/NOT_BUILT status, the reason is extracted and displayed.

## References

- [API Reference](references/api-ref.md) - Jenkins API details
- [Parameter Reference](references/parameter-ref.md) - Complete parameter documentation
- [Build Workflow](references/workflow.md) - Detailed triggering and monitoring workflow

## Anti-Patterns Checklist

| Category | Anti-Pattern | Correct Approach |
|----------|-------------|------------------|
| **Concurrency** | ❌ Allow multiple builds to run simultaneously | ✅ Always check for running tasks before trigger |
| **Trigger** | ❌ "打个包" without confirming platform/environment | ✅ Always confirm required parameters |
| **Trigger** | ❌ Skip build number notification | ✅ Immediately return `✅ 已触发 #{build_num}` after success |
| **Validation** | ❌ Allow invalid parameter combinations | ✅ Validate all rules; auto-correct where possible |
| **Error** | ❌ Vague error messages | ✅ Specific errors with actionable suggestions |
| **Log** | ❌ Output full console log in IM | ✅ Write to file, send as attachment |
| **Info** | ❌ Mix console log with build info | ✅ Separate: info shows structured data; log retrieved separately |
| **Workflow** | ❌ Skip user confirmation for destructive actions | ✅ Confirm before stop/trigger; abort on "错了"/"不对"/"停" |
| **Script** | ❌ Use raw curl for Jenkins API | ✅ Always use jenkins.py as single entry point |
| **Parameters** | ❌ Assume environment from branch name | ✅ Explicitly ask or use default; never infer |
| **Output** | ❌ Output unformatted JSON or raw API response | ✅ Structure output with clear sections and hierarchy |
