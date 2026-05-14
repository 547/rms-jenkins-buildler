# Jenkins API Reference

## Basic Information

- **Jenkins URL**: `http://your-jenkins-server:8080` (configured in `config.json`)
- **Default User**: `your_username` (configured in `config.json`)
- **Authentication**: API Token (configured in `config.json`, NOT login password)

> ⚠️ Actual credentials must be configured in `config.json`.

---

## Authentication Flow

### Step 1: Login (Save cookie)

```bash
curl -s -c cookies.txt -b cookies.txt \
  -d "j_username=${JENKINS_USER}&j_password=${JENKINS_API_TOKEN}&from=%2F&Submit=Sign+In" \
  "${JENKINS_URL}/j_spring_security_check"
```

> Note: Use API Token instead of login password for authentication.

### Step 2: Get CSRF Crumb (Required for each API request)

```bash
CRUMB=$(curl -s -b cookies.txt \
  "${JENKINS_URL}/crumbIssuer/api/json" | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['crumbRequestField']+'='+json.load(sys.stdin)['crumb'])")
```

> Crumb has a time limit (~24 hours). For frequent requests, retrieve a new crumb before each API call.

---

## Common APIs

### Query Job Status

```bash
curl -s -b cookies.txt \
  -H "crumb: $CRUMB" \
  "${JENKINS_URL}/job/your-job-name/lastBuild/api/json"
```

Returned JSON key fields:
- `result`: null = running; "SUCCESS" / "FAILURE" / "ABORTED" = finished
- `number`: build number
- `duration`: duration in milliseconds
- `url`: build URL
- `building`: true/false

### Query Specific Build Status

```bash
curl -s -b cookies.txt \
  -H "crumb: $CRUMB" \
  "${JENKINS_URL}/job/your-job-name/<buildNum>/api/json"
```

### Get Build Console Output

```bash
curl -s -b cookies.txt \
  -H "crumb: $CRUMB" \
  "${JENKINS_URL}/job/your-job-name/<buildNum>/consoleText"
```

> Extract key error messages from this output when build fails.

### Trigger Build (with parameters)

```bash
curl -s -b cookies.txt \
  -H "crumb: $CRUMB" \
  -X POST \
  "${JENKINS_URL}/job/your-job-name/buildWithParameters?platform=iOS&environment=test&uploadTarget=pgyer&needPullBranch=true"
```

> HTTP 302 redirect indicates successful trigger (queued or started).

### Get Queue Position (after trigger)

```bash
curl -s -b cookies.txt \
  -H "crumb: $CRUMB" \
  "${JENKINS_URL}/job/your-job-name/api/json?tree=queueId"
```

### Stop Build

```bash
# Stop latest build
curl -s -b cookies.txt \
  -H "crumb: $CRUMB" \
  -X POST \
  "${JENKINS_URL}/job/your-job-name/lastBuild/stop"

# Stop specific build
curl -s -b cookies.txt \
  -H "crumb: $CRUMB" \
  -X POST \
  "${JENKINS_URL}/job/your-job-name/<buildNum>/stop"
```

### View All Build History

```bash
curl -s -b cookies.txt \
  -H "crumb: $CRUMB" \
  "${JENKINS_URL}/job/your-job-name/api/json?tree=builds[number,result,building,url]"
```

---

## Build Number Extraction

After successful trigger, the Location header contains the build number:
```
Location: http://your-jenkins-server:8080/queue/item/123/
# or
Location: http://your-jenkins-server:8080/job/your-job-name/1027/
```

Extraction method:
```bash
# Extract build number from Location header
BUILD_NUM=$(echo "$LOCATION" | grep -oP 'job/your-job-name/\K\d+')
```

---

## Error Handling

| Error | Meaning | Handling |
|-------|---------|----------|
| HTTP 403 | Cookie expired or no permission | Re-authenticate to get new cookie |
| HTTP 404 | Job/build not found | Verify job name and build number |
| HTTP 403 (No valid crumb) | Crumb expired | Retrieve new crumb |
| "Please wait while Jenkins is preparing" | Jenkins is starting | Wait and retry |
