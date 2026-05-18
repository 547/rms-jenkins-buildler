# Jenkins API 参考

## API 端点

### 基础信息

- **Base URL**: 从 `config.json` 的 `JENKINS` 字段读取
- **认证**: Basic Auth（用户名 + API Token）
- **CSRF**: 需要先获取 crumb，然后在请求头中包含 `Jenkins-Crumb`

### 主要端点

#### 1. 获取 CSRF Crumb

```
GET {JENKINS}/crumbIssuer/api/json
```

**响应：**
```json
{
  "crumb": "Jenkins-Crumb:abc123",
  "crumbRequestField": "Jenkins-Crumb"
}
```

#### 2. 获取构建列表

```
GET {JENKINS}/job/{job_name}/api/json?tree=builds[number,result,building,duration,timestamp,actions[parameters[name,value]]]
```

**响应：**
```json
{
  "builds": [
    {
      "number": 123,
      "result": "SUCCESS",
      "building": false,
      "duration": 900000,
      "timestamp": 1736914200000,
      "actions": [
        {
          "parameters": [
            {"name": "platform", "value": "iOS"},
            {"name": "environment", "value": "test"}
          ]
        }
      ]
    }
  ]
}
```

#### 3. 触发构建

```
POST {JENKINS}/job/{job_name}/buildWithParameters
Content-Type: application/x-www-form-urlencoded
```

**请求体：**
```
platform=iOS&environment=test&flutterModuleBranch=master&...
```

**响应：**
- 成功：返回 201，Location 头包含队列 URL 或构建 URL
- 失败：返回 4xx/5xx 错误

#### 4. 停止构建

```
POST {JENKINS}/job/{job_name}/{build_num}/stop
```

#### 5. 获取构建日志

```
POST {JENKINS}/job/{job_name}/{build_num}/logText/progressiveText
```

**响应：**
- 成功：返回日志文本内容

#### 6. 获取队列信息

```
GET {queue_url}/api/json
```

**响应：**
```json
{
  "executable": {
    "number": 124,
    "url": "{JENKINS}/job/{job_name}/124/"
  }
}
```

## 错误码

| HTTP 状态码 | 含义 | 处理方式 |
|------------|------|---------|
| 200 | 成功 | 解析响应数据 |
| 201 | 创建成功 | 从 Location 头获取队列/构建 URL |
| 403 | 认证失败 | 重试 3 次，检查用户名和 Token |
| 404 | 资源不存在 | 提示用户检查 job 名称或构建号 |
| 500 | 服务器错误 | 提示用户联系管理员 |
| 503 | 服务不可用 | 提示用户稍后重试 |

## 重试策略

- **网络错误**: 最多重试 3 次，每次间隔 2 秒
- **认证失败（403）**: 最多重试 3 次，CSRF token 可能过期
- **队列轮询**: 最多等待 10 秒获取构建号

## 超时设置

- **请求超时**: 从 `config.json` 的 `TIMEOUT` 字段读取（默认 15 秒）
- **队列轮询超时**: 10 秒