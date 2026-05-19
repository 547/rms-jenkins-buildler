---
name: rms-jenkins-buildler
description: |
  iOS/Android Jenkins 构建管理技能。当用户提到"打包"、"构建"、"触发构建"、"查看构建状态"、"查看日志"、"停止构建"、"重新执行"、"重新打包"、"构建失败"、"构建成功"、"构建号"、"上传"、"发布"、"pgyer"、"App Store"等关键词时，立即触发此技能。
  支持单任务并发控制、自动检测运行中任务、智能参数推断、构建状态监控、日志检索。
---

# RMS Jenkins 构建管理器技能

用于执行和监控移动端应用（iOS & Android）的 Jenkins 构建流水线，支持单任务并发控制。

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

## 适用场景

当以下情况时使用此技能：
- 用户需要**触发**新的 iOS/Android Jenkins 构建
- 用户想要**查看**构建状态或**浏览**构建日志
- 用户需要**停止**运行中的构建或**重新执行**之前的构建
- 用户提到关键词："打包"、"构建"、"trigger"、"build"、"查看日志"、"停止构建"、"重新执行"、"构建状态"
- 用户想要**监控**正在进行的构建过程
- 用户需要**获取**特定构建的控制台输出

## 不适用场景

当以下情况时不使用此技能：
- 用户询问一般的 CI/CD 建议或 Jenkins 服务器配置帮助
- 用户想要修改 Jenkins job 配置或流水线定义
- 用户询问代码审查、单元测试或非 Jenkins 环境的部署
- 用户询问非 Jenkins 构建系统（如 GitLab CI、GitHub Actions）
- 用户需要查询最近几次构建之外的构建历史
- 用户想要管理 Jenkins 凭证或安全设置

## 核心功能

1. **单任务并发控制** - 同一时间只能运行一个构建任务
2. **自动检测运行中任务** - 在触发任何新构建之前，检查是否有运行中的任务
3. **智能参数推断** - 根据上传目标自动设置平台和环境
4. **强制参数确认** - 必须明确指定平台和环境参数
5. **日志文件交付** - 日志始终以文件附件形式返回给 IM 平台

## 输入 / 输出

### 输入参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `command` | string | **是** | 要执行的操作：`trigger`（触发构建）、`rerun`（重新执行）、`rerun-last`（重新执行上次）、`stop`（停止）、`stop-running`（停止运行中）、`status`（状态）、`running`（运行中任务）、`last`（最后一次）、`info`（详情）、`log-tail`（日志尾部）、`full-log`（完整日志） |
| `job` | string | 是 | Jenkins job 名称（默认为配置文件中的 `DEFAULT_JOB`） |
| `platform` | string | **是** | 目标平台：`iOS` \| `Android` \| `all` |
| `environment` | string | **是** | API 环境：`test`（测试）\| `product`（生产）\| `develop`（开发）\| `gray`（灰度）\| `preproduct`（预生产） |
| `flutterBranch` | string | 否 | Flutter 模块分支（默认：`master`） |
| `iosBranch` | string | 否 | iOS 原生分支（默认：`master`） |
| `androidBranch` | string | 否 | Android 原生分支（默认：`master`） |
| `isDebug` | boolean | 否 | Android Debug 构建标志（默认：`false`） |
| `uploadTarget` | string | 否 | 上传目标：`pgyer`（蒲公英）\| `appleAppStore`（App Store）（默认：`pgyer`） |
| `build_num` | number | 条件 | 构建号（`rerun`、`stop`、`info`、`log-tail`、`full-log` 命令必需） |
| `version` | string | 否 | 版本号（仅 iOS） |
| `updateNotes` | string | 否 | 版本更新说明（仅 iOS） |
| `submitForReview` | boolean | 否 | 自动提交 App Store 审核（默认：`false`） |
| `needPullBranch` | boolean | 否 | 构建前拉取远程分支代码（默认：`true`） |
| `isOld` | boolean | 否 | iOS 蒲公英上传旧版本兼容标志（默认：`false`，仅对 iOS 测试/生产环境有效） |

### 输出参数

| 参数 | 类型 | 描述 |
|------|------|------|
| `success` | boolean | 操作是否成功 |
| `build_num` | number | 构建号（成功触发后返回） |
| `message` | string | 人类可读的状态或结果消息 |
| `errors` | string[] | `success=false` 时的错误详情 |
| `params` | object | 验证后的最终构建参数（适用时） |
| `log_path` | string | 日志文件的绝对路径（用于 `log-tail`、`full-log`） |

#### params 对象字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `flutterModuleBranch` | string | Flutter 模块分支 |
| `iOSNativeBranch` | string | iOS 原生分支 |
| `androidNativeBranch` | string | Android 原生分支 |
| `environment` | string | API 环境 |
| `version` | string | 版本号（仅 iOS） |
| `platform` | string | 目标平台 |
| `uploadTarget` | string | 上传目标 |
| `updateNotes` | string | 版本更新说明 |
| `submitForReview` | boolean | 自动提交 App Store 审核 |
| `isDebug` | boolean | Android Debug 构建标志 |
| `needPullBranch` | boolean | 构建前拉取远程分支代码 |
| `isOld` | boolean | iOS 蒲公英上传旧版本兼容标志 |

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

## 核心命令

所有 Jenkins 操作必须通过 `jenkins.py` 执行，不要直接使用 curl。

详细命令语法和参数映射见 [参数参考](references/parameter-ref.md)。

## 参数默认值

默认参数配置见 [参数参考](references/parameter-ref.md)。

## 智能参数规则

智能参数规则见 [参数参考](references/parameter-ref.md)。

## 验证规则

参数验证规则见 [参数参考](references/parameter-ref.md)。

## 并发控制

### 运行中任务检测

在触发任何新构建（包括重新执行）之前，系统会检查运行中任务：

1. 如果发现运行中任务 → 显示构建号和业务参数
2. 询问用户是否继续（会终止运行中任务）
3. 只有用户确认后才继续

详细流程和输出格式见 [构建工作流](references/workflow.md)。

## 触发流程

详细触发流程见 [构建工作流](references/workflow.md)。

## 失败处理

### 参数验证失败

```
ERROR: 触发构建失败
HINT: platform 参数不能为空，请指定 iOS、Android 或 all
```

### 构建触发失败

```
ERROR: 触发构建失败
HINT: 请求失败 (403): Forbidden
```

### 构建失败

构建失败时显示详细信息，包括失败原因、参数和日志提示。详细格式见 [构建工作流](references/workflow.md)。

## 构建信息输出格式

构建信息输出格式见 [构建工作流](references/workflow.md)。

## 日志检索

日志检索和文件发送流程见 [构建工作流](references/workflow.md)。

## 状态输出

| 状态 | 图标 | 描述 |
|------|------|------|
| SUCCESS | ✅ | 构建成功 |
| FAILURE | ❌ | 构建失败 |
| ABORTED | ■ | 已终止 |
| RUNNING | 🔄 | 运行中 |
| NOT_BUILT | ⚠️ | 未构建 |

对于 FAILURE/ABORTED/NOT_BUILT 状态，会提取并显示失败原因。

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
- `trigger` 命令：输出构建信息到 stdout，**包含脚本返回的所有业务参数，一个不漏**：
  ```
  ✅ 已触发 {job} #{build_num}
  
  📦 构建参数：
    flutterModuleBranch: master
    iOSNativeBranch: master
    androidNativeBranch: master
    environment: test
    version:
    platform: iOS
    uploadTarget: pgyer
    updateNotes:
    submitForReview: false
    isDebug: false
    needPullBranch: true
    isOld: false
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

## 参考文档

- [API 参考](references/api-ref.md) - Jenkins API 详细说明
- [参数参考](references/parameter-ref.md) - 完整的参数文档
- [构建工作流](references/workflow.md) - 详细的触发和监控流程

## 反模式检查表

| 分类 | 反模式 | 正确做法 |
|------|--------|----------|
| **并发** | ❌ 允许多个构建同时运行 | ✅ 触发前始终检查运行中任务 |
| **触发** | ❌ "打个包" 而不确认平台/环境 | ✅ 始终确认必需参数 |
| **触发** | ❌ 跳过构建号通知 | ✅ 成功后立即返回 `✅ 已触发 #{build_num}` |
| **验证** | ❌ 允许无效参数组合 | ✅ 验证所有规则；尽可能自动修正 |
| **错误** | ❌ 模糊的错误消息 | ✅ 具体的错误信息和可操作建议 |
| **日志** | ❌ 在 IM 中输出完整控制台日志 | ✅ 写入文件，作为附件发送 |
| **信息** | ❌ 将控制台日志与构建信息混合 | ✅ 分离：info 显示结构化数据；log 单独获取 |
| **工作流** | ❌ 跳过破坏性操作的用户确认 | ✅ 停止/触发前确认；收到"错了"/"不对"/"停"时中止 |
| **脚本** | ❌ 直接使用 curl 调用 Jenkins API | ✅ 始终使用 jenkins.py 作为单一入口点 |
| **参数** | ❌ 从分支名称推断环境 | ✅ 明确询问或使用默认值；永不推断 |
| **输出** | ❌ 输出未格式化的 JSON 或原始 API 响应 | ✅ 结构化输出，使用清晰的分段和层次结构 |
