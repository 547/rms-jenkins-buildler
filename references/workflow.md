# 构建工作流

## 触发构建流程

### Step 1: 检查运行中任务

```bash
python3 jenkins.py running <job>
```

- 如果运行中 → 显示构建号和业务参数
- 询问用户是否继续（会终止运行中任务）
- 只有用户确认后才继续

### Step 2: 参数验证

- 验证 `platform` 和 `environment` 是否提供
- 应用智能参数规则
- 检查无效组合

### Step 3: 执行触发

```bash
python3 jenkins.py trigger <job> <platform> <env> <flutter> <ios> [android] [isDebug] [upload] [version] [updateNotes] [submitForReview] [needPullBranch] [isOld]
```

### Step 4: 返回结果

成功触发后立即返回：

```
✅ 已触发 my-job #124

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
  isOld: false
```

## 运行中任务检测

### 输出格式

```
发现有任务正在运行:
  Job: my-job
  Build #: #123
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

### 确认逻辑

- 用户说"继续"或"是" → 终止当前任务，触发新任务
- 用户说"取消"、"不"、"停" → 取消操作
- 用户说"错了"、"不对" → 取消操作，等待新输入

## 构建信息输出格式

### 基本信息

```
[✅ Build #123]
状态: 构建成功
触发时间: 2025-01-15 10:30:00
持续时间: 15min
```

### 失败原因

对于 FAILURE/ABORTED/NOT_BUILT 状态，显示原因：

```
--- 失败原因 ---
  error: Build failed
  /path/to/file.swift:123:45: error: cannot find 'xxx' in scope
  ^
```

### 关键参数

```
--- 参数 ---
  flutterModuleBranch = master
  iOSNativeBranch = master
  androidNativeBranch = master
  environment = test
  version = 
  platform = iOS
  uploadTarget = pgyer
  updateNotes = 
  submitForReview = false
  isDebug = false
  needPullBranch = true
  isOld = false
```

### 上传结果

**Pgyer 上传：**
```
--- 蒲公英上传 ---
  Upload to pgyer.com/k/abc123
  Build URL: https://www.pgyer.com/abc123
```

**App Store Connect 上传：**
```
--- App Store Connect 上传 ---
  Successfully uploaded package to App Store Connect
  Finished the upload to App Store Connect
  Successfully finished processing the build
```

## 日志检索

### log-tail 命令

```bash
python3 jenkins.py log-tail <job> <build_num> [n]
```

- 返回日志文件的绝对路径
- 默认行数从 `config.json` 的 `logTailLines` 读取（默认 500）
- 用户可以指定行数覆盖默认值

### full-log 命令

```bash
python3 jenkins.py full-log <job> <build_num>
```

- 返回完整日志文件的绝对路径

### 日志文件处理

**文件位置：**
```
~/.qclaw/workspace/jenkins-logs/jenkins_log_txt_{job}_{build_num}_{uuid}.txt
```

**文件内容：**
- 已去除 ANSI 转义序列
- 过滤噪音行（如 `[8mha:`）
- 保留有意义的日志内容

**自动清理：**
- 24 小时前的日志会被自动删除

### 文件发送流程

1. 脚本写入日志文件，返回绝对路径
2. Agent 使用 `openclaw message send --media <path> --channel <current_platform>` 发送文件
3. 当前平台根据会话渠道确定：feishu / wechat / other

## 状态输出

| 状态 | 图标 | 描述 |
|------|------|------|
| SUCCESS | ✅ | 构建成功 |
| FAILURE | ❌ | 构建失败 |
| ABORTED | ■ | 已终止 |
| RUNNING | 🔄 | 运行中 |
| NOT_BUILT | ⚠️ | 未构建 |