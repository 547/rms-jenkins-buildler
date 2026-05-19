---
name: rms-jenkins-buildler
description: |
  iOS/Android Jenkins 构建管理技能。当用户提到"打包"、"构建"、"触发构建"、"查看构建状态"、"查看日志"、"停止构建"、"重新执行"、"重新打包"、"构建失败"、"构建成功"、"构建号"、"上传"、"发布"、"pgyer"、"App Store"等关键词时，立即触发此技能。
  支持单任务并发控制、自动检测运行中任务、智能参数推断、构建状态监控、日志检索。
---

# RMS Jenkins 构建管理器技能

用于执行和监控移动端应用（iOS & Android）的 Jenkins 构建流水线，支持单任务并发控制。

## 适用场景

当用户需要以下操作时使用此技能：
- 触发新的 iOS/Android Jenkins 构建
- 查看构建状态或浏览构建日志
- 停止运行中的构建或重新执行之前的构建
- 监控正在进行的构建过程
- 获取特定构建的控制台输出

## 不适用场景

当以下情况时不使用此技能：
- 用户询问一般的 CI/CD 建议或 Jenkins 服务器配置帮助
- 用户想要修改 Jenkins job 配置或流水线定义
- 用户询问非 Jenkins 构建系统（如 GitLab CI、GitHub Actions）

## 核心指令

### 触发构建
1. **检查运行中任务** - 使用 `running` 命令检测，显示脚本返回的构建号、所有参数
2. **确认参数** - 必须明确 `platform` 和 `environment`
3. **触发构建** - 调用 `trigger` 命令
4. **返回结果** - 输出脚本返回的所有参数，一个不漏

### 查看状态
- 调用 `status` 命令获取构建信息
- 格式化输出运行中任务和最后一次构建状态

### 查看日志
- 使用 `log-tail` 或 `full-log` 命令
- 脚本返回日志文件路径，以附件形式发送

### 停止构建
- 确认构建号后调用 `stop` 命令
- 危险操作需用户确认

### 重新执行
- 获取原构建参数
- 检查运行中任务
- 触发新构建

## 智能参数规则

- `uploadTarget=appleAppStore` → 自动设置 `platform=iOS`, `environment=product`
- `submitForReview=true` → 自动设置 `platform=iOS`, `environment=product`, `uploadTarget=appleAppStore`

## 并发控制

触发任何构建前必须检查运行中任务：
1. 发现运行中任务 → 显示脚本返回的构建号、所有参数
2. 询问用户是否继续（会终止运行中任务）
3. 只有用户确认后才继续

## 输出格式

**触发成功：**
```
✅ 已触发 my-job #124

📦 构建参数：
  platform: iOS
  environment: test
  uploadTarget: pgyer
  submitForReview: false
  flutterModuleBranch: master
  iOSNativeBranch: master
  androidNativeBranch: master
  version:
  updateNotes:
  isDebug: false
  needPullBranch: true
  isOld: false
```

**运行中任务：**
```
发现有任务正在运行:
  Job: my-job
  Build #: #123
  参数:
    platform: iOS
    environment: test
    ...

继续新任务将终止当前任务，是否继续？
```

## 参考文档

详细信息请参考：
- [命令与参数参考](references/parameter-ref.md)
- [构建工作流](references/workflow.md)
- [API 参考](references/api-ref.md)

## 反模式检查

- ❌ 跳过运行中任务检查直接触发构建
- ❌ 不确认必需参数就执行
- ❌ 在 IM 中输出完整日志（应作为附件）
- ❌ 直接使用 curl 调用 Jenkins API（必须通过 `jenkins.py`）
