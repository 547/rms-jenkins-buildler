# 示例输入

## 场景 1：触发 iOS 测试环境构建

**用户输入：**
```
帮我打个 iOS 测试环境的包
```

**提取的参数：**
- command: trigger
- platform: iOS
- environment: test
- flutterBranch: master (默认)
- iosBranch: master (默认)
- androidBranch: master (默认)
- uploadTarget: pgyer (默认)

---

## 场景 2：触发 Android Debug 构建

**用户输入：**
```
打个 Android 的 debug 包
```

**提取的参数：**
- command: trigger
- platform: Android
- environment: test (默认)
- isDebug: true
- uploadTarget: pgyer (默认)

---

## 场景 3：上传到 App Store

**用户输入：**
```
上传到 App Store
```

**提取的参数：**
- command: trigger
- platform: iOS (自动推断)
- environment: product (自动推断)
- uploadTarget: appleAppStore
- submitForReview: false (默认)

---

## 场景 4：查看构建状态

**用户输入：**
```
查看构建状态
```

**提取的参数：**
- command: status

---

## 场景 5：查看构建日志

**用户输入：**
```
查看 #123 的日志
```

**提取的参数：**
- command: log-tail
- build_num: 123

---

## 场景 6：停止构建

**用户输入：**
```
停止 #124 的构建
```

**提取的参数：**
- command: stop
- build_num: 124

---

## 场景 7：重新执行上次构建

**用户输入：**
```
重新执行上次构建
```

**提取的参数：**
- command: rerun-last

---

## 场景 8：指定分支构建

**用户输入：**
```
用 develop 分支打个 iOS 测试包
```

**提取的参数：**
- command: trigger
- platform: iOS
- environment: test
- flutterBranch: develop
- iosBranch: develop
- uploadTarget: pgyer (默认)