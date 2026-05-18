# Build Triggering Workflow

This workflow defines the step-by-step process for triggering, monitoring, and managing Jenkins builds with single-task concurrency control.

## Core Principles

1. **Single Task Only**: Only one build task can run at a time
2. **Explicit Confirmation**: Always confirm with user before stopping running tasks
3. **Parameter Clarity**: Clearly show business parameters (platform, environment, uploadTarget, submitForReview, flutterModuleBranch, iOSNativeBranch, androidNativeBranch, version, updateNotes, isDebug, needPullBranch) for user confirmation
4. **Log as File**: Always return logs as file attachments for IM platforms

## User Intent Classification

When user wants to trigger a build, classify intent first:

| Intent | Keywords | Action |
|--------|----------|--------|
| Rerun specific | "重新执行 #xxx", "用 xxx 再打" | `rerun <job> <build_num>` |
| Rerun last | "重新执行", "再打个包", "再打" | `rerun-last <job>` |
| Trigger new | "打个包", "帮我打包" | Follow trigger flow below |
| Stop build | "停止打包", "终止打包" | `stop-running` or `stop` |

## Trigger Flow (New Build)

### Step 1: Check for Running Tasks

**Critical**: This step applies to ALL build triggers including rerun and rerun-last.

```bash
python3 jenkins.py running <job>
```

**If running task found:**
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

- **User confirms** → Stop running task, proceed with new build
- **User cancels** → Abort, do nothing

### Step 2: Parameter Confirmation

Before triggering, ensure **platform** and **environment** are explicitly specified:

```
📦 打包参数确认
- platform: iOS (必填)
- environment: test (必填)
- flutterModuleBranch: master
- iOSNativeBranch: developer
- uploadTarget: pgyer
- needPullBranch: true

打包吗？
```

**Abort conditions:**
- User says "错了", "不对", "停", "参数错了" → Stop immediately, execute nothing
- platform not specified → Ask user to specify
- environment not specified → Ask user to specify

### Step 3: Apply Smart Parameter Rules

Automatically set parameters based on special conditions:

| Condition | Auto-set Values |
|-----------|-----------------|
| `uploadTarget=appleAppStore` | `platform=iOS`, `environment=product` |
| `submitForReview=true` | `platform=iOS`, `environment=product`, `uploadTarget=appleAppStore` |

### Step 4: Validate Parameters

Validate against rules before execution:

| Rule | Behavior |
|------|----------|
| Android + develop/gray | Auto-downgrade to test, notify user |
| uploadTarget=appleAppStore + Android | Return error |
| uploadTarget=appleAppStore + environment≠product | Auto-correct to product |
| isDebug=true + platform=iOS | Return error |

### Step 5: Execute Trigger

```bash
python3 jenkins.py trigger <job> <platform> <env> <flutter> <ios> [android] [isDebug] [upload] [version] [updateNotes] [submitForReview] [needPullBranch]
```

**Critical:** After successful trigger, immediately return `✅ 已触发 #{build_num}` with business parameters.

### Step 6: Return Results

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

## Stop Flow

| User says | Command |
|-----------|---------|
| "停止打包", "终止打包" (no specific number) | `stop-running <job>` |
| "停止 #xxx", "终止 #xxx" | `stop <job> <build_num>` |

```bash
# Stop specific build
python3 jenkins.py stop <job> <build_num>

# Stop all running builds
python3 jenkins.py stop-running <job>
```

## Info Output Checklist

When displaying `info` results, follow this order:

- [ ] **Basic info**: build number, result, trigger time, duration
- [ ] **Status reason** (FAILURE/ABORTED/NOT_BUILT only): extract error/abort reasons
- [ ] **Key parameters**: platform, environment, version, platform, uploadTarget, updateNotes, submitForReview, isDebug, needPullBranch
- [ ] **Pgyer results** (SUCCESS + pgyer only): extract pgyer/buildkey/buildinfo/qrcode lines
- [ ] **App Store results** (SUCCESS + appleAppStore only): extract deliver/itunes/processing lines

**Note:** `info` does NOT output console log by default. Console logs are retrieved separately via `log-tail` or `full-log` commands to avoid IM platform message truncation.

## Status Display

| Status | Icon | Description |
|--------|------|-------------|
| SUCCESS | ✅ | 构建成功 |
| FAILURE | ❌ | 构建失败 |
| ABORTED | ■ | 已终止 |
| RUNNING | 🔄 | 运行中 |
| NOT_BUILT | ⚠️ | 未构建 |

## Log Retrieval Flow

### log-tail (Default: logTailLines from config.json)

```bash
python3 jenkins.py log-tail <job> <build_num> [n]
```

1. Script writes log to file, returns absolute path
2. Agent sends file via `openclaw message send --media <path> --channel <current_platform>`
3. Current platform: feishu / wechat / other (from session channel)

### full-log (Complete log)

```bash
python3 jenkins.py full-log <job> <build_num>
```

Same delivery flow as log-tail.

## Feedback Loop

After receiving build results:

- **SUCCESS**: Show summary + pgyer/AppStore upload info
- **FAILURE**: Show failure reasons extracted from log
- **ABORTED**: Show abortion reasons
- **RUNNING**: Show current status + estimated wait time

## Validation Script Integration

If validation fails, return structured error:

```json
{
  "success": false,
  "error": "platform 参数不能为空",
  "suggestion": "请指定 platform 参数（iOS/Android/all）"
}
```

## Common Error Handling

| Error | Handling |
|-------|----------|
| Config file missing | Instruct user to copy from config.json.example |
| HTTP 403 (auth failed) | Re-authenticate, retry once |
| HTTP 404 (job not found) | Confirm job name, list available jobs |
| Build not found | Confirm build number |
| Network timeout | Retry once, then report error |
| Running task exists | Show confirmation dialog before proceeding |
| Missing platform/environment | Ask user to specify required parameters |

## Parameter Priority

Parameters are applied in this order:

1. **User input** (highest priority)
2. **Smart parameter rules** (auto-set based on conditions)
3. **Config defaults** (from config.json DEFAULTS section)
4. **Hardcoded defaults** (fallback)

## Required Parameters

These parameters MUST be provided or will cause rejection:

- `platform` - Target platform (iOS/Android/all)
- `environment` - API environment (test/test_old/product/product_old/develop/gray/preproduct)
