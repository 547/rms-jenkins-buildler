# RMS Jenkins 构建管理器

## 命令列表

| 命令 | 语法 | 说明 |
|------|------|------|
| trigger | `trigger <job> <platform> <env> <flutter> <ios> [android] [isDebug] [upload] [version] [updateNotes] [submitForReview] [needPullBranch] [isOld]` | 触发新构建 |
| rerun | `rerun <job> <build_num>` | 重新执行指定构建 |
| rerun-last | `rerun-last <job>` | 重新执行上次构建 |
| stop | `stop <job> <build_num>` | 停止指定构建 |
| stop-running | `stop-running [job]...` | 停止运行中任务 |
| status | `status [job]...` | 查看构建状态 |
| running | `running [job]...` | 检查运行中任务 |
| last | `last <job>` | 获取最后一次构建 |
| info | `info <job> <build_num>` | 获取构建详情 |
| log-tail | `log-tail <job> <build_num> [n]` | 获取日志尾部 |
| full-log | `full-log <job> <build_num>` | 获取完整日志 |

## 触发关键词

当用户提到以下内容时调用此技能：
- "打包"、"打个包"、"构建"、"触发构建"
- "查看构建状态"、"检查运行状态"
- "停止构建"、"终止任务"、"取消构建"
- "查看日志"、"获取构建日志"
- "重新执行"、"再打一次"、"重跑"

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

**运行中任务检测：**
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
    iOSNativeBranch: master
    androidNativeBranch: master
    version:
    updateNotes:
    isDebug: false
    needPullBranch: true
    isOld: false

继续新任务将终止当前任务，是否继续？
```

**状态查询：**
```
[my-job]
  🔄 #124 运行中 (5min)
  上次: #123 ✅ 构建成功 (15min)
```

## 必需参数

| 参数 | 类型 | 说明 |
|------|------|------|
| platform | string | `iOS` \| `Android` \| `all` |
| environment | string | `test` \| `product` \| `develop` \| `gray` \| `preproduct` |

## 智能参数规则

- `uploadTarget=appleAppStore` → `platform=iOS`, `environment=product`
- `submitForReview=true` → `platform=iOS`, `environment=product`, `uploadTarget=appleAppStore`

## 并发控制流程

1. 使用 `running` 命令检查运行中任务
2. 如果存在运行中任务，显示脚本返回的构建号、所有参数
3. 询问用户是否继续（会终止运行中任务）
4. 只有用户确认后才继续

## 错误处理

**缺少必需参数：**
```
ERROR: platform 参数不能为空，请指定 iOS、Android 或 all
```

**API 错误：**
```
ERROR: 触发构建失败
HINT: 请求失败 (403): Forbidden
```

## 调用方式

```bash
python3 {skill_dir}/scripts/jenkins.py <command> [args...]
```
