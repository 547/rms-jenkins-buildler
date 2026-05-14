# Parameter Reference

Complete parameter documentation for Jenkins build jobs with single-task concurrency control.

## Parameter Summary

| Parameter | Type | Default | Required | Platform | Description |
|-----------|------|---------|----------|----------|-------------|
| `platform` | enum | `iOS` | **YES** | All | Target platform |
| `environment` | enum | `test` | **YES** | All | API environment |
| `flutterModuleBranch` | string | `master` | No | All | Flutter module remote branch |
| `iOSNativeBranch` | string | `master` | No | iOS/all | iOS native remote branch |
| `androidNativeBranch` | string | `master` | No | Android/all | Android native remote branch |
| `uploadTarget` | enum | `pgyer` | No | All | Upload destination |
| `version` | string | (empty) | No | iOS only | Version number |
| `updateNotes` | string | (auto) | No | iOS only | Version update notes |
| `submitForReview` | boolean | `false` | No | iOS+AppStore | Auto submit for review |
| `isDebug` | boolean | `false` | No | Android only | Build debug variant |
| `needPullBranch` | boolean | `true` | No | All | Pull remote branch code |

## Required Parameters

### platform (Target Platform)

**Required:** Yes

| Value | Description |
|-------|-------------|
| `iOS` | iOS only (default) |
| `Android` | Android only |
| `all` | Both iOS and Android |

### environment (API Environment)

**Required:** Yes

| Value | Description | Android Support |
|-------|-------------|-----------------|
| `test` | Test environment | ✅ |
| `product` | Production environment | ✅ |
| `develop` | Development environment | ❌ (auto-downgrade to test) |
| `gray` | Gray environment | ❌ (auto-downgrade to test) |
| `preproduct` | Pre-production environment | ✅ |

## Optional Parameters

### uploadTarget (Upload Destination)

| Value | Description | Platform Restriction |
|-------|-------------|---------------------|
| `pgyer` | Upload to Pgyer (蒲公英) | iOS + Android |
| `appleAppStore` | Upload to App Store | iOS only |

**Special Behavior:**
- When `uploadTarget=appleAppStore`, `platform` is automatically set to `iOS` and `environment` is automatically set to `product`.

### submitForReview (Auto Submit for Review)

| Value | Description |
|-------|-------------|
| `true` | Auto submit to App Store review after upload |
| `false` | Do not auto submit (default) |

**Special Behavior:**
- When `submitForReview=true`:
  - `platform` is automatically set to `iOS`
  - `environment` is automatically set to `product`
  - `uploadTarget` is automatically set to `appleAppStore`

### isDebug (Debug Build)

| Value | Description | Platform Restriction |
|-------|-------------|---------------------|
| `true` | Build debug variant | Android only |
| `false` | Build release variant (default) | All |

### needPullBranch (Pull Remote Code)

| Value | Description |
|-------|-------------|
| `true` | Jenkins pulls latest code from remote branch before build (default) |
| `false` | Uses locally cached code (faster, for testing) |

## Smart Parameter Rules

These rules are automatically applied when triggering builds:

| Condition | Action |
|-----------|--------|
| `uploadTarget=appleAppStore` | Auto-set `platform=iOS`, `environment=product` |
| `submitForReview=true` | Auto-set `platform=iOS`, `environment=product`, `uploadTarget=appleAppStore` |

## Validation Rules

### Rule Matrix

| Condition | Result | Message |
|-----------|--------|---------|
| `platform` not specified | Reject | "platform 参数不能为空" |
| `environment` not specified | Reject | "environment 参数不能为空" |
| Android + develop/gray | Auto-downgrade to test | "Android 不支持 {env}，已降级为 test" |
| appleAppStore + Android | Reject | "Android 不支持上传 App Store" |
| appleAppStore + environment≠product | Auto-correct | Auto-set to product |
| isDebug=true + platform=iOS | Reject | "isDebug=true 仅对 Android 有效" |

### Validation Code

```python
def validate_params(params):
    errors = []
    warnings = []

    p = params.get("platform", "")
    e = params.get("environment", "")
    u = params.get("uploadTarget", "")
    vd = params.get("isDebug", "false")

    # Required parameter validation
    if not p:
        errors.append("platform 参数不能为空")
    if not e:
        errors.append("environment 参数不能为空")

    # Android environment validation
    if p in ("Android", "all") and e in ("develop", "gray"):
        params["environment"] = "test"
        warnings.append(f"Android 不支持 {e}，已降级为 test")

    # uploadTarget validation
    if u == "appleAppStore" and p == "Android":
        errors.append("Android 不支持上传 App Store")

    # isDebug validation
    if vd == "true" and p not in ("Android", "all"):
        errors.append("isDebug=true 仅对 Android 有效")

    return errors, warnings
```

## Environment + UploadTarget Combinations

| platform | uploadTarget | environment | Valid | Auto-correction |
|----------|-------------|------------|-------|-----------------|
| iOS | pgyer | test | ✅ | - |
| iOS | pgyer | product | ✅ | - |
| iOS | appleAppStore | test | ❌ | environment → product |
| iOS | appleAppStore | product | ✅ | - |
| Android | pgyer | test | ✅ | - |
| Android | pgyer | product | ✅ | - |
| Android | pgyer | develop | ❌ | environment → test |
| Android | pgyer | gray | ❌ | environment → test |
| all | pgyer | test | ✅ | - |
| all | pgyer | product | ✅ | - |

## Parameter Dependencies

```
platform
├── iOS
│   └── uses: iOSNativeBranch, version, updateNotes, submitForReview
├── Android
│   └── uses: androidNativeBranch, isDebug
└── all
    └── uses: iOSNativeBranch, androidNativeBranch
```

## Special Parameters

### version (iOS only)
- Version number for the build
- If empty, Jenkins may auto-generate

### updateNotes (iOS only)
- Version update notes
- If empty, auto-generated from last 5 commit messages

### submitForReview (iOS + appleAppStore only)
- Auto submit to App Store review after upload
- Only effective when uploadTarget=appleAppStore
- When set to `true`, automatically sets platform=iOS, environment=product

## Concurrency Control

### Running Task Detection

Before triggering ANY new build (including rerun), the system checks for running tasks:

1. If running task found → Display build_num and all parameters
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
    flutterModuleBranch: master
    iOSNativeBranch: developer

继续新任务将终止当前任务，是否继续？
```

## Log Configuration

### logTailLines

- Default number of lines for `log-tail` command
- Configured in `config.json`
- Default value: 500
- User can override by specifying line count: `log-tail <job> <build_num> 1000`

## Configuration Example

```json
{
  "JENKINS": "http://your-jenkins-server:8080",
  "USER": "your_jenkins_username",
  "TOKEN": "your_jenkins_api_token_here",
  "TIMEOUT": 15,
  "DEFAULT_JOB": "your-default-job-name",
  "DEFAULTS": {
    "flutterModuleBranch": "master",
    "iOSNativeBranch": "master",
    "androidNativeBranch": "master",
    "environment": "test",
    "platform": "iOS",
    "uploadTarget": "pgyer",
    "version": "",
    "updateNotes": "",
    "submitForReview": "false",
    "isDebug": "false",
    "needPullBranch": "true"
  },
  "logTailLines": 500
}
```
