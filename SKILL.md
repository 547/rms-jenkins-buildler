---
name: rms-jenkins-buildler
description: |
  iOS/Android Jenkins 构建管理技能。当用户提到"打包"、"构建"、"触发构建"、"查看构建状态"、"查看日志"、"停止构建"、"重新执行"、"重新打包"、"构建失败"、"构建成功"、"构建号"、"上传"、"发布"、"pgyer"、"App Store"等关键词时，立即触发此技能。
  支持单任务并发控制、自动检测运行中任务、智能参数推断、构建状态监控、日志检索。
---

# RMS Jenkins Buildler Skill

Execute and monitor Jenkins build pipelines for mobile apps (iOS & Android) with single-task concurrency control.

## 快速开始

### 示例 1：触发 iOS 测试环境构建

**用户输入：**
```
帮我打个 iOS 测试环境的包
```

**Agent 执行步骤：**
1. 检查是否有运行中的任务
2. 验证参数：platform=iOS, environment=test
3. 触发构建
4. 返回构建号和参数

**输出：**
```
✅ 已触发 my-job #124

📦 构建参数：
  platform: iOS
  environment: test
  uploadTarget: pgyer
  flutterModuleBranch: master
  iOSNativeBranch: master
```

### 示例 2：查看构建状态

**用户输入：**
```
查看构建状态
```

**Agent 执行步骤：**
1. 调用 `status` 命令
2. 解析返回结果
3. 格式化输出

**输出：**
```
[my-job]
  No running jobs
  Last: #123 ✅ 构建成功 (15min)
```

### 示例 3：重新执行上次构建

**用户输入：**
```
重新执行上次构建
```

**Agent 执行步骤：**
1. 获取最后一次构建信息
2. 提取参数
3. 检查是否有运行中任务
4. 触发新构建

**输出：**
```
重新执行 my-job #123
  新构建号: #125

📦 构建参数：
  platform: iOS
  environment: test
  uploadTarget: pgyer
```

## When to Use

Use this skill when:
- User needs to **trigger** a new Jenkins build for iOS/Android apps
- User wants to **check** build status or **view** build logs
- User needs to **stop** a running build or **rerun** a previous build
- User mentions keywords: "打包", "构建", "trigger", "build", "查看日志", "停止构建", "重新执行", "构建状态"
- User wants to **monitor** an ongoing build process
- User needs to **retrieve** console output from a specific build

## When NOT to Use

Do NOT use this skill when:
- User asks for general CI/CD advice or Jenkins server configuration help
- User wants to modify Jenkins job configurations or pipeline definitions
- User asks about code review, unit testing, or deployment to non-Jenkins environments
- User asks about non-Jenkins build systems (e.g., GitLab CI, GitHub Actions)
- User needs to query build history beyond the last few builds
- User wants to manage Jenkins credentials or security settings

## Core Features

1. **Single-Task Concurrency Control** - Only one build task can run at a time
2. **Automatic Running Task Detection** - Before triggering any new build, checks for running tasks
3. **Smart Parameter Inference** - Automatically sets platform and environment based on upload target
4. **Mandatory Parameter Confirmation** - platform and environment must be explicitly specified
5. **Log File Delivery** - Logs are always returned as file attachments for IM platforms

## Input / Output

### Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `command` | string | **Yes** | Action to perform: `trigger`, `rerun`, `rerun-last`, `stop`, `stop-running`, `status`, `running`, `last`, `info`, `log-tail`, `full-log` |
| `job` | string | Yes | Jenkins job name (defaults to `DEFAULT_JOB` from config) |
| `platform` | string | **Yes** | Target platform: `iOS` \| `Android` \| `all` |
| `environment` | string | **Yes** | API environment: `test` \| `test_old` \| `product` \| `product_old` \| `develop` \| `gray` \| `preproduct` |
| `flutterBranch` | string | No | Flutter module branch (default: `master`) |
| `iosBranch` | string | No | iOS native branch (default: `master`) |
| `androidBranch` | string | No | Android native branch (default: `master`) |
| `isDebug` | boolean | No | Android debug build flag (default: `false`) |
| `uploadTarget` | string | No | Upload destination: `pgyer` \| `appleAppStore` (default: `pgyer`) |
| `build_num` | number | Conditional | Build number (required for `rerun`, `stop`, `info`, `log-tail`, `full-log`) |
| `version` | string | No | Version number (iOS only) |
| `updateNotes` | string | No | Version update notes (iOS only) |
| `submitForReview` | boolean | No | Auto submit for App Store review (default: `false`) |
| `needPullBranch` | boolean | No | Pull remote branch code before build (default: `true`) |

### Output

| Parameter | Type | Description |
|-----------|------|-------------|
| `success` | boolean | Whether the operation succeeded |
| `build_num` | number | Build number (returned after successful trigger) |
| `message` | string | Human-readable status or result message |
| `errors` | string[] | Error details when `success=false` |
| `params` | object | Final build parameters after validation (when applicable) |
| `log_path` | string | Absolute path to log file (for `log-tail`, `full-log`) |

## 工作流 / 执行步骤

### 触发构建工作流

当用户请求触发新构建时，按以下步骤执行：

1. **检查运行中任务**
   - 调用 `running` 命令检测是否有任务正在运行
   - 如果有运行中任务，显示任务详情（构建号、参数）并询问用户是否继续
   - 等待用户确认后再继续（避免误操作终止正在进行的构建）

2. **提取和验证参数**
   - 从用户输入中提取 `platform` 和 `environment` 参数（必填）
   - 如果用户未指定，明确询问用户
   - 应用智能参数规则（如 uploadTarget=appleAppStore 自动设置 platform=iOS）
   - 验证参数组合的有效性（如 Android 不支持 appleAppStore）

3. **触发构建**
   - 调用 `trigger` 命令执行构建
   - 等待 Jenkins 返回构建号
   - 立即向用户返回构建号和最终参数

4. **返回结果**
   - 格式化输出构建信息
   - 包含构建号、平台、环境、上传目标等关键信息

### 查看构建状态工作流

当用户请求查看构建状态时，按以下步骤执行：

1. **调用状态命令**
   - 执行 `status` 命令获取构建信息
   - 解析返回的 JSON 数据

2. **格式化输出**
   - 显示运行中的任务（如果有）
   - 显示最后一次构建的状态和持续时间
   - 使用图标标识不同状态（✅ 成功、❌ 失败、🔄 运行中）

### 查看构建日志工作流

当用户请求查看构建日志时，按以下步骤执行：

1. **确定日志范围**
   - 如果用户指定行数，使用指定值
   - 否则使用配置文件中的 `logTailLines` 默认值（500）

2. **获取日志内容**
   - 调用 `log-tail` 或 `full-log` 命令
   - 脚本将日志写入文件并返回文件路径

3. **发送日志文件**
   - 使用 `openclaw message send --media <path>` 发送文件
   - 确保文件路径是绝对路径
   - 根据当前会话平台选择正确的渠道

### 停止构建工作流

当用户请求停止构建时，按以下步骤执行：

1. **确认构建号**
   - 如果用户未指定构建号，询问用户
   - 确保构建号有效

2. **执行停止操作**
   - 调用 `stop` 命令
   - 等待 Jenkins 确认停止

3. **返回结果**
   - 通知用户构建已停止
   - 显示停止的构建号

### 重新执行构建工作流

当用户请求重新执行构建时，按以下步骤执行：

1. **确定要重新执行的构建**
   - 如果用户指定构建号，使用该构建
   - 否则获取最后一次构建

2. **提取原构建参数**
   - 调用 `info` 命令获取构建详情
   - 提取所有构建参数

3. **检查运行中任务**
   - 遵循触发构建工作流中的步骤 1

4. **触发新构建**
   - 使用原构建参数触发新构建
   - 返回新构建号和参数

## Core Commands

所有 Jenkins 操作必须通过 `jenkins.py` 执行，不要直接使用 curl。

详细命令语法和参数映射见 [参数参考](references/parameter-ref.md)。

## Parameter Defaults

默认参数配置见 [参数参考](references/parameter-ref.md)。

## Smart Parameter Rules

智能参数规则见 [参数参考](references/parameter-ref.md)。

## Validation Rules

参数验证规则见 [参数参考](references/parameter-ref.md)。

## Concurrency Control

### Running Task Detection

在触发任何新构建（包括重新执行）之前，系统会检查运行中任务：

1. 如果发现运行中任务 → 显示构建号和业务参数
2. 询问用户是否继续（会终止运行中任务）
3. 只有用户确认后才继续

详细流程和输出格式见 [构建工作流](references/workflow.md)。

## Trigger Flow

详细触发流程见 [构建工作流](references/workflow.md)。

## On Failure

### Parameter Validation Failure

```
ERROR: 触发构建失败
HINT: platform 参数不能为空，请指定 iOS、Android 或 all
```

### Build Trigger Failure

```
ERROR: 触发构建失败
HINT: 请求失败 (403): Forbidden
```

### Build Failure

构建失败时显示详细信息，包括失败原因、参数和日志提示。详细格式见 [构建工作流](references/workflow.md)。

## Build Info Output Format

构建信息输出格式见 [构建工作流](references/workflow.md)。

## Log Retrieval

日志检索和文件发送流程见 [构建工作流](references/workflow.md)。

## Status Output

| Status | Icon | Description |
|--------|------|-------------|
| SUCCESS | ✅ | 构建成功 |
| FAILURE | ❌ | 构建失败 |
| ABORTED | ■ | 已终止 |
| RUNNING | 🔄 | 运行中 |
| NOT_BUILT | ⚠️ | 未构建 |

For FAILURE/ABORTED/NOT_BUILT status, the reason is extracted and displayed.

## 附加资源引用

### scripts/ 目录

**何时使用：**
- 所有 Jenkins API 调用必须通过 `scripts/jenkins.py` 执行
- 不要直接使用 curl 或其他工具访问 Jenkins API

**如何使用：**
```bash
# 触发构建
python3 {skill_dir}/scripts/jenkins.py trigger <job> <platform> <env> <flutter> <ios>

# 查看状态
python3 {skill_dir}/scripts/jenkins.py status <job>

# 获取日志
python3 {skill_dir}/scripts/jenkins.py log-tail <job> <build_num>
```

**脚本输出格式：**

所有脚本命令遵循以下输出规范：

**成功情况（退出码 0）：**
- `trigger` 命令：输出构建信息到 stdout，格式为：
  ```
  ✅ 已触发 {job} #{build_num}
  
  📦 构建参数：
    {参数名}: {参数值}
  ```
- `status` 命令：输出状态信息到 stdout
- `log-tail` / `full-log` 命令：输出日志文件的绝对路径到 stdout
- 其他命令：输出操作结果到 stdout

**失败情况（退出码非 0）：**
- 输出错误信息到 stderr，格式为：
  ```
  ERROR: {错误标题}
  HINT: {详细说明和恢复建议}
  ```
- 输出警告信息到 stderr，格式为：
  ```
  WARNING: {警告内容}
  ```
- 输出信息到 stdout，格式为：
  ```
  INFO: {信息内容}
  ```
- 输出成功信息到 stdout，格式为：
  ```
  SUCCESS: {成功内容}
  ```

**日志文件处理：**
- 日志文件自动清理：24 小时前的日志会被自动删除
- 日志文件位置：`~/.qclaw/workspace/jenkins-logs/`
- 日志文件命名：`jenkins_log_{suffix}_{job}_{build_num}_{uuid}.txt`
- 日志内容：已去除 ANSI 转义序列，过滤噪音行

### evals.json

**何时使用：**
- 运行自我测试时自动加载
- 定义测试用例、反馈规则、学习规则

**如何使用：**
```bash
# 运行自我测试
python3 {skill_dir}/scripts/jenkins.py self-test

# 执行自我进化分析
python3 {skill_dir}/scripts/jenkins.py evolve
```

### config.json

**何时使用：**
- 脚本启动时自动加载
- 包含 Jenkins 服务器配置和默认参数

**必需字段：**
- `JENKINS`: Jenkins 服务器 URL
- `USER`: Jenkins 用户名
- `TOKEN`: Jenkins API Token

**可选字段：**
- `DEFAULT_JOB`: 默认 Job 名称
- `TIMEOUT`: 请求超时时间（秒）
- `logTailLines`: 日志默认行数
- `DEFAULTS`: 默认构建参数

### learning_data.json

**何时使用：**
- 自动生成，用于存储学习数据
- 记录错误模式、用户偏好参数

**如何使用：**
- 由脚本自动管理
- 用户无需手动编辑

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
