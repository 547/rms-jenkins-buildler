# 参数参考

## 构建参数

### 必填参数

| 参数名 | 类型 | 说明 | 可选值 |
|--------|------|------|--------|
| `platform` | string | 目标平台 | `iOS`, `Android`, `all` |
| `environment` | string | API 环境 | `test`, `test_old`, `product`, `product_old`, `develop`, `gray`, `preproduct` |

### 可选参数

| 参数名 | 类型 | 默认值 | 说明 | 适用平台 |
|--------|------|--------|------|---------|
| `flutterModuleBranch` | string | `master` | Flutter 模块分支 | iOS, Android, all |
| `iOSNativeBranch` | string | `master` | iOS 原生分支 | iOS, all |
| `androidNativeBranch` | string | `master` | Android 原生分支 | Android, all |
| `isDebug` | boolean | `false` | Android Debug 构建 | Android, all |
| `uploadTarget` | string | `pgyer` | 上传目标 | iOS, Android, all |
| `version` | string | 空 | 版本号（iOS） | iOS, all |
| `updateNotes` | string | 空 | 版本更新说明（iOS） | iOS, all |
| `submitForReview` | boolean | `false` | 自动提交 App Store 审核 | iOS, all |
| `needPullBranch` | boolean | `true` | 是否拉取远程分支代码 | iOS, Android, all |

## 配置参数

### config.json 必填字段

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `JENKINS` | string | Jenkins 服务器 URL | `http://jenkins.example.com` |
| `USER` | string | Jenkins 用户名 | `admin` |
| `TOKEN` | string | Jenkins API Token | `abc123def456` |

### config.json 可选字段

| 字段名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `DEFAULT_JOB` | string | 空 | 默认 Job 名称 |
| `TIMEOUT` | number | 15 | 请求超时时间（秒） |
| `logTailLines` | number | 500 | 日志默认行数 |
| `DEFAULTS` | object | `{}` | 默认构建参数 |

## 智能参数规则

### 规则 1：uploadTarget=appleAppStore

**触发条件：** 用户指定 `uploadTarget=appleAppStore`

**自动设置：**
- `platform=iOS`
- `environment=product`

**原因：** App Store 只接受 iOS 平台的正式版本

### 规则 2：submitForReview=true

**触发条件：** 用户指定 `submitForReview=true`

**自动设置：**
- `platform=iOS`
- `environment=product`
- `uploadTarget=appleAppStore`

**原因：** 只有 iOS 平台才能提交 App Store 审核

### 规则 3：Android + develop/gray 环境

**触发条件：** `platform=Android` 且 `environment=develop` 或 `gray`

**自动修正：**
- `environment=test`

**原因：** Android 不支持 develop 和 gray 环境

### 规则 4：Android + appleAppStore

**触发条件：** `platform=Android` 且 `uploadTarget=appleAppStore`

**结果：** 参数验证失败

**错误信息：** "Android 不支持上传 App Store，请选择其他上传目标（如 pgyer）"

## 参数验证规则

### 必填检查

- `platform` 不能为空
- `environment` 不能为空

### 值有效性检查

| 参数 | 有效值 | 无效值示例 |
|------|--------|-----------|
| `platform` | `iOS`, `Android`, `all` | `Windows`, `Linux` |
| `environment` | `test`, `test_old`, `product`, `product_old`, `develop`, `gray`, `preproduct` | `staging`, `production` |

### 组合有效性检查

| 组合 | 结果 | 说明 |
|------|------|------|
| `platform=Android` + `uploadTarget=appleAppStore` | ❌ 失败 | Android 不能上传 App Store |
| `platform=iOS` + `isDebug=true` | ❌ 失败 | isDebug 仅对 Android 有效 |
| `platform=Android` + `environment=develop` | ⚠️ 警告 | 自动降级为 test |
| `uploadTarget=appleAppStore` + `environment=test` | ⚠️ 警告 | 自动修正为 product |

## 命令行参数映射

### trigger 命令

```bash
python3 jenkins.py trigger <job> <platform> <env> <flutter> <ios> [android] [isDebug] [upload] [version] [updateNotes] [submitForReview] [needPullBranch]
```

| 位置 | 参数名 | 说明 |
|------|--------|------|
| 1 | `job` | Job 名称 |
| 2 | `platform` | 目标平台 |
| 3 | `env` | API 环境 |
| 4 | `flutter` | Flutter 分支 |
| 5 | `ios` | iOS 分支 |
| 6 | `android` | Android 分支 |
| 7 | `isDebug` | Debug 标志 |
| 8 | `upload` | 上传目标 |
| 9 | `version` | 版本号 |
| 10 | `updateNotes` | 更新说明 |
| 11 | `submitForReview` | 提交审核 |
| 12 | `needPullBranch` | 拉取分支 |

### 其他命令

```bash
# 状态
python3 jenkins.py status [job...]

# 运行中
python3 jenkins.py running [job...]

# 重新执行
python3 jenkins.py rerun <job> <build_num>

# 重新执行最后一次
python3 jenkins.py rerun-last [job]

# 停止
python3 jenkins.py stop <job> <build_num>

# 停止所有运行中
python3 jenkins.py stop-running [job...]

# 构建信息
python3 jenkins.py info <job> <build_num>

# 最后一次构建
python3 jenkins.py last <job>

# 日志尾部
python3 jenkins.py log-tail <job> <build_num> [n]

# 完整日志
python3 jenkins.py full-log <job> <build_num>
```