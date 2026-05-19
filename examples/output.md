# 示例输出

## 场景 1：触发 iOS 测试环境构建

**输出：**
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

---

## 场景 2：触发 Android Debug 构建

**输出：**
```
✅ 已触发 my-job #125

📦 构建参数：
  platform: Android
  environment: test
  uploadTarget: pgyer
  submitForReview: false
  flutterModuleBranch: master
  iOSNativeBranch: master
  androidNativeBranch: master
  version:
  updateNotes:
  isDebug: true
  needPullBranch: true
  isOld: false
```

---

## 场景 3：上传到 App Store

**输出：**
```
INFO: 检测到 uploadTarget=appleAppStore，自动设置 platform=iOS, environment=product
✅ 已触发 my-job #126

📦 构建参数：
  platform: iOS
  environment: product
  uploadTarget: appleAppStore
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

---

## 场景 4：查看构建状态

**输出：**
```
[my-job]
  No running jobs
  Last: #123 ✅ 构建成功 (15min)
```

**有运行中任务时：**
```
[my-job]
  🔄 #124 运行中 (5min)
  上次: #123 ✅ 构建成功 (15min)
```

---

## 场景 5：查看构建日志

**输出：**
```
/Users/username/.qclaw/workspace/jenkins-logs/jenkins_log_txt_my-job_123_abc12345.txt
```

（Agent 会将此文件发送给用户）

---

## 场景 6：停止构建

**输出：**
```
已停止 my-job #124
```

---

## 场景 7：重新执行上次构建

**输出：**
```
重新执行 my-job #123
  新构建号: #125

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

---

## 场景 8：有运行中任务时触发新构建

**输出：**
```
发现有任务正在运行:
  Job: my-job
  Build #: #124
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
    needPullBranch: false
    isOld: false

继续新任务将终止当前任务，是否继续？
```

（Agent 需要等待用户确认）

---

## 场景 9：参数验证失败

**输出：**
```
ERROR: 触发构建失败
HINT: platform 参数不能为空，请指定 iOS、Android 或 all
```

---

## 场景 10：参数组合无效

**输出：**
```
ERROR: 触发构建失败
HINT: Android 不支持上传 App Store，请选择其他上传目标（如 pgyer）
```

---

## 场景 11：构建信息详情

**输出：**
```
[✅ Build #123]
状态: 构建成功
触发时间: 2025-01-15 10:30:00
持续时间: 15min

--- 参数 ---
  platform = iOS
  environment = test
  uploadTarget = pgyer
  submitForReview = false
  flutterModuleBranch = master
  iOSNativeBranch = master
  androidNativeBranch = master
  version = 
  updateNotes = 
  isDebug = false
  needPullBranch = true
  isOld = false

--- 蒲公英上传 ---
  Upload to pgyer.com/k/abc123
  Build URL: https://www.pgyer.com/abc123

执行 'log-tail my-job 123' 查看最后 500 行日志
```

---

## 场景 12：构建失败

**输出：**
```
[❌ Build #125]
状态: 构建失败
触发时间: 2025-01-15 11:00:00
持续时间: 8min

--- 失败原因 ---
  error: Build failed
  /path/to/file.swift:123:45: error: cannot find 'xxx' in scope
  ^

--- 参数 ---
  platform = iOS
  environment = test
  uploadTarget = pgyer
  submitForReview = false
  flutterModuleBranch = develop
  iOSNativeBranch = develop
  androidNativeBranch = master
  version = 
  updateNotes = 
  isDebug = false
  needPullBranch = true
  isOld = false

执行 'log-tail my-job 125' 查看最后 500 行日志
```
