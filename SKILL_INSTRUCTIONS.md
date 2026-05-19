# RMS Jenkins 构建管理器

## 命令列表

| 命令 | 语法 |
|------|------|
| trigger | `trigger <job> <platform> <env> <flutter> <ios> [android] [isDebug] [upload] [version] [updateNotes] [submitForReview] [needPullBranch] [isOld]` |
| rerun | `rerun <job> <build_num>` |
| rerun-last | `rerun-last <job>` |
| stop | `stop <job> <build_num>` |
| stop-running | `stop-running [job]...` |
| status | `status [job]...` |
| running | `running [job]...` |
| last | `last <job>` |
| info | `info <job> <build_num>` |
| log-tail | `log-tail <job> <build_num> [n]` |
| full-log | `full-log <job> <build_num>` |

## 适用场景

当用户提到以下内容时调用此技能：
- "打包"、"打个包"、"构建"
- "触发 Jenkins"、"开始构建"
- "查看构建状态"、"检查运行状态"
- "停止构建"、"终止任务"
- "查看日志"、"获取构建日志"
- "重新执行"、"再打一次"

## 输出解释

**成功响应：**
- `✅ 已触发 #{build_num}` - 构建触发成功，**输出脚本返回的所有参数，一个不漏**：
  ```
  ✅ 已触发 my-job #124
  
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
- `发现有任务正在运行:` - 显示运行中任务详情（**包含所有业务参数，一个不漏**），需要用户确认
- `NONE` - 没有运行中的任务
- 日志命令返回文件路径

**错误响应：**
- "platform 参数不能为空" - 缺少必需参数
- "environment 参数不能为空" - 缺少必需参数
- "API Error HTTP XXXX" - Jenkins API 错误

## 使用示例

```bash
# 触发构建
python3 {skill_dir}/scripts/jenkins.py trigger myjob iOS test master master

# 查看状态
python3 {skill_dir}/scripts/jenkins.py status

# 停止构建
python3 {skill_dir}/scripts/jenkins.py stop myjob 123

# 获取日志
python3 {skill_dir}/scripts/jenkins.py log-tail myjob 123
```

## 并发控制

触发任何构建之前：
1. 使用 `running` 命令检查运行中任务
2. 如果存在运行中任务，显示详情并请求确认
3. 只有用户确认终止后才继续

## 智能参数规则

- `uploadTarget=appleAppStore` → 自动设置 `platform=iOS`, `environment=product`
- `submitForReview=true` → 自动设置 `platform=iOS`, `environment=product`, `uploadTarget=appleAppStore`

## 环境选项

| 环境 | 描述 | Android 支持 |
|------|------|-------------|
| `test` | 测试环境 | ✅ |
| `product` | 生产环境 | ✅ |
| `develop` | 开发环境 | ❌ (自动降级为 test) |
| `gray` | 灰度环境 | ❌ (自动降级为 test) |
| `preproduct` | 预生产环境 | ✅ |
