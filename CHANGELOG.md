# Changelog

All notable changes to this project will be documented in this file.

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
| `trigger <job> <platform> <env> <flutter> <ios> [android] [isDebug] [upload]` | Trigger new build |
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

