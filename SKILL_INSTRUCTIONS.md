# rms-jenkins-buildler

## Commands

| Command | Syntax |
|---------|--------|
| trigger | `trigger <job> <platform> <env> <flutter> <ios> [android] [isDebug] [upload] [version] [updateNotes] [submitForReview] [needPullBranch]` |
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

## When to Use

Invoke this skill when user mentions:
- "打包", "打个包", "构建"
- "触发 Jenkins", "开始构建"
- "查看构建状态", "检查运行状态"
- "停止构建", "终止任务"
- "查看日志", "获取构建日志"
- "重新执行", "再打一次"

## Output Interpretation

**Success Response:**
- `✅ 已触发 #{build_num}` - Build triggered successfully
- `Found running jobs:` - Shows running task details, requires user confirmation
- `NONE` - No running tasks
- File path returned for log commands

**Error Response:**
- "platform 参数不能为空" - Missing required parameter
- "environment 参数不能为空" - Missing required parameter
- "API Error HTTP XXXX" - Jenkins API error

## Examples

```
# Trigger build
python3 {skill_dir}/scripts/jenkins.py trigger myjob iOS test master master

# Check status
python3 {skill_dir}/scripts/jenkins.py status

# Stop build
python3 {skill_dir}/scripts/jenkins.py stop myjob 123

# Get log
python3 {skill_dir}/scripts/jenkins.py log-tail myjob 123
```

## Concurrency Control

Before triggering any build:
1. Check for running tasks with `running` command
2. If running task exists, show details and ask for confirmation
3. Only proceed after user confirms termination

## Smart Parameter Rules

- `uploadTarget=appleAppStore` → auto-set `platform=iOS`, `environment=product`
- `submitForReview=true` → auto-set `platform=iOS`, `environment=product`, `uploadTarget=appleAppStore`
