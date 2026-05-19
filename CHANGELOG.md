# Changelog

All notable changes to this project will be documented in this file.

## [1.2.1] - 2026-05-19

### Updated

- **文档结构优化**:
  - `SKILL.md`: 精简为 112 行，去除重复内容，保持核心指令简洁
  - `SKILL_INSTRUCTIONS.md`: 作为 Agent 操作指南，包含命令列表、触发关键词、输出格式
  - `references/workflow.md`: 详细工作流说明，参数顺序与脚本实际输出一致
  - `examples/output.md`: 统一参数顺序，与脚本输出保持一致

- **参数顺序统一**: 所有文档中构建参数顺序与 `jenkins.py` 脚本实际输出一致

- **语言一致性**: 确保所有文档语言统一为中文

## [1.2.0] - 2026-05-19

### Added

- **isOld 参数**: 新增 `isOld` 布尔参数
  - 用于旧版本兼容（仅对上传到蒲公英时的iOS测试环境、生产环境有效，即蒲公英渠道不一样）
  - 默认值：`false`
  - 仅对 iOS 平台有效

### Removed

- **移除 test_old 和 product_old 环境**
  - 删除了 `test_old` 环境选项
  - 删除了 `product_old` 环境选项
  - 旧版本兼容功能现在通过 `isOld` 参数实现

### Updated

- **更新所有文档**:
  - `SKILL.md`: 更新 Input/Output 参数表，添加 `params` 对象字段详情，统一文档语言为中文
  - `SKILL_INSTRUCTIONS.md`: 更新 trigger 命令语法，统一文档语言为中文
  - `references/parameter-ref.md`: 更新参数说明和 trigger 命令
  - `references/workflow.md`: 更新 trigger 命令语法和返回结果示例
  - `config.json.example`: 更新示例配置
  - `CHANGELOG.md`: 更新 Core Commands 表格

- **更新脚本代码**:
  - `jenkins.py`: 更新参数验证逻辑，移除旧环境，添加 `isOld` 参数支持
  - 更新 `key_params` 列表，包含 `isOld` 参数
  - 更新命令行参数解析，支持第13个参数 `isOld`

- **文档语言统一**: 将所有文档中的英文内容统一为中文，确保语言一致性

### Test Verification

自我测试全部通过:

| 测试 | 状态 |
|------|------|
| 触发 iOS 测试环境构建 | ✅ 通过 |
| 触发 Android Debug 构建 | ✅ 通过 |
| 验证缺少 platform 参数 | ✅ 通过 |
| 验证缺少 environment 参数 | ✅ 通过 |
| 验证 Android 不能上传 App Store | ✅ 通过 |
| 智能参数：appleAppStore 自动设置 | ✅ 通过 |
| Android 环境自动降级 | ✅ 通过 |
| 验证无效平台值 | ✅ 通过 |

## [1.1.0] - 2026-05-18

### Added

- **快速开始示例**: 新增详细的快速开始指南，包含 4 个实际使用示例
  - iOS 测试环境构建
  - Android Debug 构建
  - App Store 上传
  - 查看构建状态/日志等

- **examples/ 目录**: 新增示例文件
  - `input.md`: 8 个场景的用户输入示例
  - `output.md`: 12 个场景的脚本输出示例

- **references/ 目录**: 新增参考文档
  - `api-ref.md`: Jenkins API 端点、错误码、重试策略
  - `parameter-ref.md`: 构建参数、配置参数、智能规则、验证规则
  - `workflow.md`: 触发流程、运行中任务检测、构建信息输出、日志检索

- **自我进化功能**: 新增自我学习和进化能力
  - `run_self_test()`: 基于 evals.json 的自动化测试
  - `learn_from_error()`: 从错误中学习，记录错误模式
  - `learn_preferred_params()`: 学习用户偏好参数
  - `auto_evolve()`: 基于学习数据提供改进建议

- **evals.json**: 新增评测配置文件
  - 10 个测试用例覆盖参数验证和智能推断
  - 反馈规则定义用户交互处理
  - 学习规则定义自动优化策略

### Updated

- **SKILL.md 优化**:
  - 从 563 行精简到 430 行，符合最佳实践
  - description 增加中文关键词，触发更精准
  - 新增"工作流/执行步骤"章节，详细描述 5 个主要操作
  - 新增"附加资源引用"章节，详细说明 scripts/、evals.json、config.json、learning_data.json
  - 新增"脚本输出格式"详细说明
  - 详细内容拆分到 references/ 目录，保持主文档简洁

- **脚本输出格式规范化**:
  - 成功：返回 0，输出结构化信息到 stdout
  - 失败：返回非 0，ERROR/HINT 输出到 stderr
  - 警告：WARNING 输出到 stderr
  - 信息：INFO 输出到 stderr
  - 日志文件：返回绝对路径到 stdout

### Test Verification

自我测试全部通过:

| 测试 | 状态 |
|------|------|
| 触发 iOS 测试环境构建 | ✅ 通过 |
| 触发 Android Debug 构建 | ✅ 通过 |
| 验证缺少 platform 参数 | ✅ 通过 |
| 验证缺少 environment 参数 | ✅ 通过 |
| 验证 Android 不能上传 App Store | ✅ 通过 |
| 智能参数：appleAppStore 自动设置 | ✅ 通过 |
| Android 环境自动降级 | ✅ 通过 |
| 验证无效平台值 | ✅ 通过 |

## [1.0.1] - 2026-05-18

### Added

- **New Environment Options**: Added `test_old` and `product_old` environment options
  - `test_old`: Test environment (legacy compatibility, different iOS Pgyer channel)
  - `product_old`: Production environment (legacy compatibility, different iOS Pgyer channel)
  - Both environments are supported on both iOS and Android platforms
  - Android platform only auto-downgrades `develop`/`gray` to `test`

### Updated

- Updated all documentation to include new environment options
- Updated parameter validation logic to support new environments

## [1.0.0] - 2026-05-14

### Added

- **Single-Task Concurrency Control**: Only one build task can run at a time
  - Automatic detection of running tasks before triggering new builds
  - User confirmation required before terminating running tasks
  - Returns running task details (job name, build number, parameters)

- **Smart Parameter Inference**: Automatically sets parameters based on context
  - `uploadTarget=appleAppStore` → `platform=iOS`, `environment=product`
  - `submitForReview=true` → `platform=iOS`, `environment=product`, `uploadTarget=appleAppStore`

- **Mandatory Parameter Validation**
  - `platform` and `environment` are required parameters
  - Android does not support `develop`/`gray` environments (auto-downgrade to test)
  - `isDebug=true` only valid for Android platform
  - Android does not support App Store upload

- **Log File Output**
  - `log-tail` command writes last N lines to file (default: 500)
  - `full-log` command writes complete log to file
  - Returns absolute file path for IM platform file delivery

- **Actual Build Parameters Return**
  - After successful trigger, queries Jenkins API to get actual recorded parameters
  - Ensures returned parameters match what Jenkins actually used

### Core Commands

| Command | Description |
|---------|-------------|
| `trigger <job> <platform> <env> <flutter> <ios> [android] [isDebug] [upload] [version] [updateNotes] [submitForReview] [needPullBranch] [isOld]` | Trigger new build |
| `rerun <job> <build_num>` | Rerun specific build |
| `rerun-last <job>` | Rerun last build |
| `stop <job> <build_num>` | Stop specific build |
| `stop-running [job]...` | Stop all running builds |
| `status [job]...` | Check build status |
| `running [job]...` | Check running tasks |
| `info <job> <build_num>` | Get detailed build info |
| `last <job>` | Get last build info |
| `log-tail <job> <build_num> [n]` | Get last N lines of log (file output) |
| `full-log <job> <build_num>` | Get full log (file output) |

### Configuration

- `config.json.example` - Template for configuration
- `DEFAULT_JOB` - Default Jenkins job name
- `logTailLines` - Default log lines for log-tail command
- `TIMEOUT` - API request timeout

### Test Verification

All core functions tested successfully:

| Function | Status |
|----------|--------|
| `running` command | ✅ Passed |
| `status` command | ✅ Passed |
| `last` command | ✅ Passed |
| `trigger` command | ✅ Passed (successfully triggered build #1106) |
| `stop` command | ✅ Passed (successfully stopped build #1106) |
| Concurrent task detection | ✅ Passed |
| Parameter validation | ✅ Passed |
| Log file output | ✅ Passed |
| Jenkins API integration | ✅ Passed |

### Updated Tests (2026-05-14)

Additional tests completed successfully:

| Function | Status |
|----------|--------|
| `stop-running` command | ✅ Passed |
| `rerun` command | ✅ Passed (successfully reran build #1108 → #1109) |
| `log-tail` command | ✅ Passed (returns file path correctly) |
| Parameter confirmation flow | ✅ Passed (platform/environment confirmation before trigger) |
| Smart parameter inference | ✅ Passed |
| Concurrency control | ✅ Passed (confirms before terminating running tasks) |

### Known Issues

- Jenkins API may take a few seconds to reflect status changes after stop command
- Build status API may return "Cannot get status" for newly triggered builds (transient)

