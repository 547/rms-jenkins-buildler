#!/usr/bin/env python3
"""
Jenkins Build Manager Script

This script provides a comprehensive interface for managing Jenkins builds with:
- Single-task concurrency control (prevents concurrent builds)
- Automatic running task detection before triggering new builds
- Smart parameter inference (auto-sets platform/env based on upload target)
- Robust error handling with retry mechanisms
- Structured logging and file delivery
- Config validation and error recovery

Core Features:
- Multi-layer error handling with configurable retry policies
- Input validation with actionable error messages
- Clean log file management with automatic cleanup
- Consistent output format for IM platforms

Usage:
    python3 jenkins.py <command> [options]

Commands:
    status [job...]              - Check build status for specified jobs
    running [job...]             - Check if any build is currently running
    trigger <job> <platform> <env> <flutter> <ios> [android] [isDebug] [upload] [version] [updateNotes] [submitForReview] [needPullBranch]
    rerun <job> <build_num>      - Rerun a specific build with original parameters
    rerun-last [job]             - Rerun the most recent completed build
    stop <job> <build_num>       - Stop a specific running build
    stop-running [job...]        - Stop all running builds for specified jobs
    info <job> <build_num>       - Get detailed information for a specific build
    last [job]                   - Get information for the last completed build
    log-tail <job> <build_num> [n] - Get last N lines of console log (default: 500)
    full-log <job> <build_num>   - Get complete console log

Error Handling:
- Network errors: Retry 3 times with 2s delay
- Authentication errors: Retry 3 times (CSRF token may expire)
- Config errors: Clear instructions for recovery
"""

import json
import urllib.request
import urllib.parse
import base64
import sys
import time
import uuid
import datetime
import glob
import re
import os
from typing import Dict, List, Optional, Tuple, Any

# Configuration paths
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "config.json")
_EXAMPLE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "config.json.example")

# Constants
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2
LOG_TAIL_LINES_DEFAULT = 500
OLD_LOG_CLEANUP_HOURS = 24


def _load_config() -> Dict[str, Any]:
    """Load and validate the configuration file.
    
    Returns:
        Configuration dictionary with validated fields.
    
    Raises:
        SystemExit: If config file is missing, invalid, or missing required fields.
    """
    if not os.path.exists(_CONFIG_PATH):
        print_error(
            "配置文件缺失", 
            f"配置文件 {_CONFIG_PATH} 不存在。\n"
            f"请按以下步骤配置：\n"
            f"1. 复制模板: cp {_EXAMPLE_PATH} {_CONFIG_PATH}\n"
            f"2. 编辑 {_CONFIG_PATH} 填写以下必填字段：\n"
            f"   - JENKINS: Jenkins 服务器 URL（如 http://jenkins.example.com）\n"
            f"   - USER: Jenkins 用户名\n"
            f"   - TOKEN: Jenkins API Token（在用户设置中生成）\n"
            f"3. 保存后重新运行"
        )
        sys.exit(1)
    
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except json.JSONDecodeError as e:
        print_error("配置文件格式错误", f"JSON 解析失败: {e}\n请检查配置文件是否为有效的 JSON 格式")
        sys.exit(1)
    except IOError as e:
        print_error("配置文件读取失败", f"无法读取配置文件: {e}\n请检查文件权限")
        sys.exit(1)
    
    required_fields = ["JENKINS", "USER", "TOKEN"]
    missing = [f for f in required_fields if f not in cfg or not cfg[f]]
    if missing:
        print_error("配置文件缺少必填字段", f"缺少字段: {', '.join(missing)}\n请确保配置文件包含所有必填字段")
        sys.exit(1)
    
    # Validate Jenkins URL format
    if not cfg["JENKINS"].startswith(("http://", "https://")):
        print_warning("Jenkins URL 格式警告", f"JENKINS 配置建议以 http:// 或 https:// 开头")
    
    return cfg


def print_error(title: str, message: str) -> None:
    """Print a formatted error message with title and actionable details.
    
    Args:
        title: Short error category/title
        message: Detailed error description with recovery suggestions
    """
    print(f"ERROR: {title}")
    print(f"HINT: {message}")


def print_warning(message: str) -> None:
    """Print a formatted warning message for non-critical issues.
    
    Args:
        message: Warning content
    """
    print(f"WARNING: {message}")


def print_info(message: str) -> None:
    """Print a formatted informational message.
    
    Args:
        message: Information content
    """
    print(f"INFO: {message}")


def print_success(message: str) -> None:
    """Print a formatted success message.
    
    Args:
        message: Success content
    """
    print(f"SUCCESS: {message}")


# Load configuration
try:
    _cfg = _load_config()
    JENKINS = _cfg["JENKINS"]
    USER = _cfg["USER"]
    TOKEN = _cfg["TOKEN"]
    TIMEOUT = int(_cfg.get("TIMEOUT", 15))
    DEFAULT_JOB = _cfg.get("DEFAULT_JOB", "")
    DEFAULTS = _cfg.get("DEFAULTS", {})
    LOG_TAIL_LINES = int(_cfg.get("logTailLines", LOG_TAIL_LINES_DEFAULT))
except SystemExit:
    raise
except Exception as e:
    print_error("配置加载失败", str(e))
    sys.exit(1)


def _cleanup_old_logs(max_age_hours: int = OLD_LOG_CLEANUP_HOURS) -> int:
    """Clean up log files older than specified hours."""
    count = 0
    cutoff = time.time() - max_age_hours * 3600
    log_dir = os.path.expanduser("~/.qclaw/workspace/jenkins-logs")
    if not os.path.isdir(log_dir):
        return 0
    
    for path in glob.glob(log_dir + "/jenkins_log_*.txt"):
        try:
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
                count += 1
        except Exception as e:
            print_warning(f"删除旧日志文件失败: {path} - {e}")
    
    return count


# Clean up old logs on startup
_cleanup_old_logs()


def cred() -> Dict[str, str]:
    """Generate authorization header for Jenkins API."""
    return {"Authorization": "Basic " + base64.b64encode((USER + ":" + TOKEN).encode()).decode()}


def get_crumb() -> str:
    """Get CSRF crumb for Jenkins API requests."""
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            req = urllib.request.Request(JENKINS + "/crumbIssuer/api/json", headers=cred())
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.load(r)["crumb"]
        except Exception as e:
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                print_warning(f"获取 CSRF crumb 失败，重试中 ({attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                print_error("获取 CSRF crumb 失败", f"已重试 {MAX_RETRY_ATTEMPTS} 次仍失败: {e}")
                raise


def api(url: str, method: str = "GET", data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Make an API request to Jenkins with comprehensive error handling.
    
    Args:
        url: The API endpoint URL
        method: HTTP method (GET, POST, etc.)
        data: POST data as dictionary
        params: Query parameters as dictionary
    
    Returns:
        Dictionary containing response data with status field.
        - status: "ok" for success, "error" for failure
        - code: HTTP status code
        - body: Response body (truncated to 500 chars for errors)
        - Location: Redirect location if present
    
    Retry Policy:
        - Network errors: Retry MAX_RETRY_ATTEMPTS times with RETRY_DELAY_SECONDS delay
        - HTTP 403 (auth failure): Retry as CSRF token may have expired
    """
    if params:
        sep = "&" if "?" in url else "?"
        url += sep + urllib.parse.urlencode(params)
    
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            crumb = get_crumb()
            headers = {**cred(), "Jenkins-Crumb": crumb}
            
            if data:
                headers["Content-Type"] = "application/x-www-form-urlencoded"
                data_encoded = urllib.parse.urlencode(data).encode()
            else:
                data_encoded = None
            
            req = urllib.request.Request(url, data=data_encoded, headers=headers, method=method)
            
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                body = r.read()
                result: Dict[str, Any] = {"status": "ok", "code": r.status}
                
                loc = r.headers.get("Location")
                if loc:
                    result["Location"] = loc
                
                if r.status == 200 and body:
                    try:
                        return {**result, **json.loads(body)}
                    except json.JSONDecodeError:
                        pass
                
                return result
        
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            error_info = {"status": "error", "http": e.code, "body": body[:500]}
            
            if e.code == 403:
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    print_warning(f"认证失败，可能需要重新获取 crumb，重试中 ({attempt + 1}/{MAX_RETRY_ATTEMPTS})")
                    time.sleep(RETRY_DELAY_SECONDS)
                    continue
                else:
                    print_error("Jenkins 认证失败", "请检查用户名和 API Token 是否正确")
            elif e.code == 404:
                print_error("资源未找到", f"Job 或构建不存在: {url}")
            elif e.code == 500:
                print_error("Jenkins 服务器错误", f"HTTP 500: 服务器内部错误，body: {body[:200]}")
            elif e.code == 503:
                print_error("Jenkins 服务不可用", f"HTTP 503: 服务暂时不可用，请稍后重试")
            else:
                print_error(f"HTTP 请求失败", f"HTTP {e.code}: {body[:200]}")
            
            return error_info
        
        except urllib.error.URLError as e:
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                print_warning(f"网络请求失败，重试中 ({attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}")
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            else:
                print_error("网络请求失败", f"已重试 {MAX_RETRY_ATTEMPTS} 次仍失败: {e}")
                return {"status": "error", "http": -1, "body": str(e)}
        
        except Exception as e:
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                print_warning(f"请求异常，重试中 ({attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}")
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            else:
                print_error("请求异常", f"已重试 {MAX_RETRY_ATTEMPTS} 次仍失败: {e}")
                return {"status": "error", "http": -1, "body": str(e)}


def strip_ansi(line: str) -> str:
    """Remove ANSI escape sequences from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", line)


def is_noisy_line(line: str, min_len: int = 0) -> bool:
    """Check if a line contains noisy or unimportant content."""
    stripped = line.strip()
    return (
        "ha://" in stripped
        or "[8mha:" in stripped
        or (min_len > 0 and len(stripped) < min_len)
    )


def format_params_for_display(params: Dict[str, Any]) -> str:
    """
    Format business parameters for display.
    
    Args:
        params: Dictionary of build parameters
    
    Returns:
        Formatted string with business parameters
    """
    business_params = [
        "platform", "environment", "uploadTarget", "submitForReview",
        "flutterModuleBranch", "iOSNativeBranch", "androidNativeBranch",
        "version", "updateNotes", "isDebug", "needPullBranch"
    ]
    lines = []
    for key in business_params:
        if key in params:
            val = str(params[key]) if params[key] is not None else ""
            lines.append(f"  {key}: {val}")
    return "\n".join(lines)


def find_running(jobs: Optional[List[str]] = None) -> List[Tuple[str, int, Dict[str, Any]]]:
    """
    Find running builds for specified jobs.
    
    Args:
        jobs: List of job names to check (defaults to DEFAULT_JOB)
    
    Returns:
        List of tuples containing (job_name, build_number, parameters)
    """
    if jobs is None:
        jobs = [DEFAULT_JOB]
    
    running = []
    for job in jobs:
        if not job:
            print_warning("未指定 job 名称，请在 config.json 中配置 DEFAULT_JOB")
            continue
        
        builds = get_builds(job, "number,building,actions[parameters[name,value]]")
        if builds is None:
            continue
        
        for b in builds:
            if b.get("building"):
                params = {}
                for a in b.get("actions", []):
                    if "parameters" in a:
                        for p in a["parameters"]:
                            params[p["name"]] = p["value"]
                running.append((job, b["number"], params))
    
    return running


def has_running_build(job: Optional[str] = None) -> bool:
    """Check if there's any running build for the specified job."""
    if job is None:
        job = DEFAULT_JOB
    running = find_running([job])
    return len(running) > 0


def get_builds(job: str, fields: str = "number,result,building,duration,timestamp,actions[parameters[name,value]]") -> Optional[List[Dict[str, Any]]]:
    """
    Get build information for a job.
    
    Args:
        job: Job name
        fields: Fields to retrieve from Jenkins API
    
    Returns:
        List of build dictionaries or None on error
    """
    d = api(f"{JENKINS}/job/{job}/api/json", params={"tree": f"builds[{fields}]"})
    if d.get("status") == "error":
        print_error("获取构建信息失败", f"Job: {job}")
        return None
    return d.get("builds", [])


def _parse_build(b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse build information from Jenkins API response.
    
    Args:
        b: Raw build data from Jenkins API
    
    Returns:
        Parsed build dictionary with parameters and abort reason
    """
    params = {}
    abort_reason = None
    
    for a in b.get("actions", []):
        cls = a.get("_class", "")
        if "parameters" in a:
            for p in a["parameters"]:
                params[p["name"]] = p["value"]
        if cls == "jenkins.model.InterruptedBuildAction" and "causes" in a:
            for cause in a["causes"]:
                desc = cause.get("shortDescription", "")
                if desc:
                    abort_reason = desc
                    break
    
    return {
        "number": b["number"],
        "result": b.get("result"),
        "building": b.get("building"),
        "duration": b.get("duration", 0),
        "timestamp": b.get("timestamp"),
        "params": params,
        "abort_reason": abort_reason,
    }


def get_build_params(job: str, build_num: int) -> Optional[Dict[str, Any]]:
    """
    Get detailed parameters for a specific build.
    
    Args:
        job: Job name
        build_num: Build number
    
    Returns:
        Build parameters or None if not found
    """
    builds = get_builds(job, "number,result,building,duration,timestamp,actions[_class,parameters[name,value],causes[shortDescription]]")
    if builds is None:
        return None
    
    for b in builds:
        if str(b["number"]) == str(build_num):
            return _parse_build(b)
    
    print_error("构建不存在", f"Job: {job}, Build #: {build_num}")
    return None


def get_last_build(job: str) -> Optional[Dict[str, Any]]:
    """
    Get the last completed build for a job.
    
    Args:
        job: Job name
    
    Returns:
        Last completed build information or None
    """
    builds = get_builds(job, "number,result,building,duration,timestamp,actions[_class,parameters[name,value],causes[shortDescription]]")
    if builds is None:
        return None
    
    for b in builds:
        if not b.get("building"):
            return _parse_build(b)
    
    return None


def fetch_build_log(job: str, build_num: int) -> str:
    """
    Fetch the complete console log for a build.
    
    Args:
        job: Job name
        build_num: Build number
    
    Returns:
        Console log text or error message
    """
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            crumb = get_crumb()
            req = urllib.request.Request(
                f"{JENKINS}/job/{job}/{build_num}/logText/progressiveText",
                headers={**cred(), "Jenkins-Crumb": crumb},
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read().decode("utf-8", errors="replace")
        
        except Exception as e:
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                print_warning(f"获取日志失败，重试中 ({attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                return f"Failed to fetch log: {e}"


def get_build_log_tail(job: str, build_num: int, n: int = 20) -> str:
    """
    Get the last N lines of console log.
    
    Args:
        job: Job name
        build_num: Build number
        n: Number of lines to retrieve
    
    Returns:
        Last N lines of console log
    """
    text = fetch_build_log(job, build_num)
    if text.startswith("Failed to fetch log"):
        return text
    
    lines = text.split("\n")
    return "\n".join(lines[-n:])


def apply_smart_defaults(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply smart parameter rules based on special conditions.
    
    Rules:
    - uploadTarget=appleAppStore → auto-set platform=iOS, environment=product
    - submitForReview=true → auto-set platform=iOS, environment=product, uploadTarget=appleAppStore
    
    Args:
        params: Input parameters
    
    Returns:
        Modified parameters with smart defaults applied
    """
    u = params.get("uploadTarget", "")
    s = params.get("submitForReview", "false")
    
    if u == "appleAppStore":
        print_info("检测到 uploadTarget=appleAppStore，自动设置 platform=iOS, environment=product")
        params["platform"] = "iOS"
        params["environment"] = "product"
    
    if s == "true":
        print_info("检测到 submitForReview=true，自动设置 platform=iOS, environment=product, uploadTarget=appleAppStore")
        params["submitForReview"] = "true"
        params["platform"] = "iOS"
        params["environment"] = "product"
        params["uploadTarget"] = "appleAppStore"
    
    return params


def validate_params(params: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """
    Validate build parameters according to business rules.
    
    This function performs comprehensive validation of build parameters,
    including required fields, valid values, and parameter combinations.
    
    Args:
        params: Input parameters to validate. Will be modified in-place for auto-corrections.
    
    Returns:
        Tuple of (is_valid, errors, warnings)
        - is_valid: True if all required parameters are valid
        - errors: List of error messages for invalid parameters
        - warnings: List of warnings for auto-corrected parameters
    
    Validation Rules:
        - platform and environment are required
        - Android doesn't support develop/gray environments (auto-downgrade to test)
        - Android doesn't support appleAppStore upload target
        - isDebug only valid for Android
        - appleAppStore requires environment=product
    """
    errors = []
    warnings = []
    p = params.get("platform", "")
    e = params.get("environment", "")
    u = params.get("uploadTarget", "")
    vd = params.get("isDebug", "false")

    # Required parameter validation
    if not p:
        errors.append("platform 参数不能为空，请指定 iOS、Android 或 all")
    elif p not in ("iOS", "Android", "all"):
        errors.append(f"platform 参数值 '{p}' 无效，可选值: iOS、Android、all")
    
    if not e:
        errors.append("environment 参数不能为空，请指定测试环境")
    elif e not in ("test", "test_old", "product", "product_old", "develop", "gray", "preproduct"):
        errors.append(f"environment 参数值 '{e}' 无效，可选值: test、test_old、product、product_old、develop、gray、preproduct")
    
    # Android environment validation (auto-downgrade)
    if p in ("Android", "all") and e in ("develop", "gray"):
        params["environment"] = "test"
        warnings.append(f"Android 不支持 {e} 环境，已自动降级为 test")

    # uploadTarget validation
    if u == "appleAppStore" and p == "Android":
        errors.append("Android 不支持上传 App Store，请选择其他上传目标（如 pgyer）")
    
    # Auto-correct environment for appleAppStore
    if u == "appleAppStore" and e != "product":
        params["environment"] = "product"
        warnings.append(f"uploadTarget=appleAppStore 要求 environment=product，已自动修正")

    # isDebug validation
    if vd == "true" and p not in ("Android", "all"):
        errors.append("isDebug=true 仅对 Android 平台有效")
    
    # version/updateNotes validation (iOS only)
    if params.get("version") and p not in ("iOS", "all"):
        warnings.append("version 参数仅对 iOS 平台有效")
    
    if params.get("updateNotes") and p not in ("iOS", "all"):
        warnings.append("updateNotes 参数仅对 iOS 平台有效")
    
    # submitForReview validation
    if params.get("submitForReview") == "true" and p not in ("iOS", "all"):
        errors.append("submitForReview=true 仅对 iOS 平台有效")

    return len(errors) == 0, errors, warnings


def trigger(job: str, **kwargs: Any) -> Tuple[bool, str, Optional[int], Dict[str, Any]]:
    """
    Trigger a new build with the specified parameters.
    
    Args:
        job: Job name
        **kwargs: Build parameters
    
    Returns:
        Tuple of (success, message, build_number, final_params)
    """
    params = dict(DEFAULTS)
    for k, v in kwargs.items():
        if v is not None and v != "":
            params[k] = v
    
    # Apply smart defaults
    params = apply_smart_defaults(params)
    
    # Validate parameters
    ok, errors, warnings = validate_params(params)
    if not ok:
        return False, "\n".join(errors), None, params
    
    # Print warnings if any
    for warning in warnings:
        print_warning(warning)
    
    # Check for running tasks
    running_list = find_running([job])
    if running_list:
        running_info = []
        for j, n, r_params in running_list:
            running_info.append(f"  Job: {j}")
            running_info.append(f"  Build #: #{n}")
            running_info.append("  Params:")
            running_info.append(format_params_for_display(r_params))
        
        message = "发现有任务正在运行:\n" + "\n".join(running_info) + "\n\n继续新任务将终止当前任务，是否继续？"
        return False, message, None, params
    
    # Execute trigger
    result = api(f"{JENKINS}/job/{job}/buildWithParameters", method="POST", data=params)
    if result.get("status") == "error":
        error_msg = f"API 错误 HTTP {result.get('http')}: {result.get('body', '')[:200]}"
        return False, error_msg, None, params

    loc = result.get("Location", "")
    if not loc:
        return True, "构建已触发", None, params

    build_num = None
    
    if "/queue/item/" in loc:
        build_num = _poll_build_num_from_queue(loc)
    elif "/job/" in loc:
        m = re.search(r'/(\d+)/?$', loc)
        if m:
            build_num = int(m.group(1))
        else:
            build_num = _poll_build_num_from_queue(loc)
    
    actual_params = params
    if build_num is not None:
        for retry in range(5):
            build_info = get_build_params(job, build_num)
            if build_info and "params" in build_info and build_info["params"]:
                actual_params = build_info["params"]
                break
            if retry < 4:
                time.sleep(1)
    
    return True, "ok", build_num, actual_params


def _poll_build_num_from_queue(queue_url: str, max_wait: int = 10) -> Optional[int]:
    """
    Poll Jenkins queue to get build number after triggering.
    
    Args:
        queue_url: Queue item URL
        max_wait: Maximum wait time in seconds
    
    Returns:
        Build number or None if not found
    """
    for _ in range(max_wait):
        time.sleep(1)
        result = api(queue_url + "/api/json")
        if result.get("status") != "ok":
            continue
        
        try:
            exe = result.get("executable", {})
            if exe:
                bn = exe.get("number")
                if bn:
                    return int(bn)
        except Exception as e:
            print_warning(f"解析队列响应失败: {e}")
            continue
    
    print_warning(f"轮询 {max_wait} 秒后仍未获取到构建号")
    return None


def stop(job: str, build_num: int) -> Tuple[bool, str]:
    """
    Stop a running build.
    
    Args:
        job: Job name
        build_num: Build number
    
    Returns:
        Tuple of (success, message)
    """
    result = api(f"{JENKINS}/job/{job}/{build_num}/stop", method="POST")
    if result.get("status") == "error":
        return False, f"HTTP {result.get('http')}: {result.get('body', '')[:200]}"
    return True, "ok"


def stop_all(jobs: Optional[List[str]] = None) -> List[Tuple[str, int, bool, str]]:
    """
    Stop all running builds for specified jobs.
    
    Args:
        jobs: List of job names (defaults to DEFAULT_JOB)
    
    Returns:
        List of results containing (job, build_num, success, message)
    """
    if jobs is None:
        jobs = [DEFAULT_JOB]
    
    results = []
    for job in jobs:
        for j, n, _ in find_running([job]):
            ok, msg = stop(j, n)
            results.append((j, n, ok, msg))
    
    return results


def rerun(job: str, build_num: int) -> Tuple[bool, str, Optional[int], Dict[str, Any]]:
    """
    Rerun a specific build with its original parameters.
    
    Args:
        job: Job name
        build_num: Build number to rerun
    
    Returns:
        Tuple of (success, message, new_build_number, parameters)
    """
    info = get_build_params(job, build_num)
    if info is None:
        return False, f"无法找到 {job} #{build_num} 的参数", None, {}
    
    if info.get("building"):
        return False, f"{job} #{build_num} 仍在运行，请先停止", None, {}

    params = info["params"]
    ok, msg, new_build, _ = trigger(job, **params)
    
    if not ok:
        return False, msg, None, params
    
    return True, msg, new_build, params


def cmd_status(jobs: List[str]) -> None:
    """Display status for specified jobs."""
    for job in jobs:
        builds = get_builds(job)
        if builds is None:
            print(f"Error: {job}: 无法获取状态")
            continue
        
        running_list = [
            (b["number"], b.get("duration", 0) // 60000, _get_build_params_from_build(b))
            for b in builds if b.get("building")
        ]
        last = next((b for b in builds if not b.get("building")), None)
        
        print(f"\n[{job}]")
        if running_list:
            for n, dur, params in running_list:
                print(f"  Running: #{n} ({dur}min)")
                if params:
                    print(f"    Params: {format_params_for_display(params)}")
        else:
            print("  No running jobs")
        
        if last:
            r = last.get("result") or "SUCCESS"
            icon = "✅" if r == "SUCCESS" else ("❌" if r == "FAILURE" else ("■" if r == "ABORTED" else "⚠️"))
            status_text = {
                "SUCCESS": "构建成功",
                "FAILURE": "构建失败",
                "ABORTED": "已终止",
                "NOT_BUILT": "未构建"
            }.get(r, r)
            print(f"  Last: #{last['number']} {icon} {status_text} ({last.get('duration', 0) // 60000}min)")


def _get_build_params_from_build(b: Dict[str, Any]) -> Dict[str, Any]:
    """Extract parameters from build data."""
    params = {}
    for a in b.get("actions", []):
        if "parameters" in a:
            for p in a["parameters"]:
                params[p["name"]] = p["value"]
    return params


def cmd_running(jobs: List[str]) -> None:
    """Check if any builds are running for specified jobs."""
    found = find_running(jobs)
    if not found:
        print("NONE")
    else:
        for j, n, params in found:
            params_str = ",".join([f"{k}={v}" for k, v in params.items()])
            print(f"{j}|{n}|{params_str}")


def cmd_trigger(job: str, platform: Optional[str] = None, env: Optional[str] = None, 
                flutter: Optional[str] = None, ios: Optional[str] = None, 
                android: str = "master", is_debug: str = "false", upload: str = "pgyer", 
                version: str = "", update_notes: str = "", submit_for_review: str = "false", 
                need_pull_branch: str = "true") -> None:
    """Trigger a new build with specified parameters."""
    params = {
        "platform": platform, "environment": env,
        "flutterModuleBranch": flutter, "iOSNativeBranch": ios,
        "androidNativeBranch": android,
        "uploadTarget": upload, "isDebug": is_debug,
        "version": version, "updateNotes": update_notes,
        "submitForReview": submit_for_review,
        "needPullBranch": need_pull_branch,
    }
    
    # Validate required parameters
    if not platform:
        print_error("缺少必填参数", "platform 参数不能为空，请指定 iOS、Android 或 all")
        return
    if not env:
        print_error("缺少必填参数", "environment 参数不能为空，请指定测试环境")
        return
    
    ok, msg, build_num, final_params = trigger(job, **params)
    
    if not ok:
        if "发现有任务正在运行" in msg:
            print(msg)
        else:
            print_error("触发构建失败", msg)
        return
    
    print(f"✅ 已触发 {job} #{build_num}")
    print("\n📦 构建参数：")
    print(format_params_for_display(final_params))


def cmd_rerun(job: str, build_num: int) -> None:
    """Rerun a specific build."""
    ok, msg, new_build, params = rerun(job, build_num)
    
    if not ok:
        if "发现有任务正在运行" in msg:
            print(msg)
        else:
            print_error("重新执行失败", msg)
        return
    
    print(f"重新执行 {job} #{build_num}")
    if new_build:
        print(f"  新构建号: #{new_build}")
    print("\n📦 构建参数：")
    print(format_params_for_display(params))


def cmd_rerun_last(job: str) -> None:
    """Rerun the last completed build."""
    last = get_last_build(job)
    if last is None:
        print_error("获取构建信息失败", f"未找到 {job} 的历史构建")
        return
    
    ok, msg, new_build, params = rerun(job, last["number"])
    
    if not ok:
        if "发现有任务正在运行" in msg:
            print(msg)
        else:
            print_error("重新执行失败", msg)
        return
    
    print(f"重新执行 {job} #{last['number']}")
    if new_build:
        print(f"  新构建号: #{new_build}")
    print("\n📦 构建参数：")
    print(format_params_for_display(params))


def cmd_stop(job: str, build_num: int) -> None:
    """Stop a specific build."""
    ok, msg = stop(job, build_num)
    if not ok:
        print_error("停止构建失败", msg)
    else:
        print(f"已停止 {job} #{build_num}")


def cmd_stop_running(jobs: List[str]) -> None:
    """Stop all running builds for specified jobs."""
    results = stop_all(jobs)
    if not results:
        print("没有运行中的任务")
    else:
        for j, n, ok, msg in results:
            if ok:
                print(f"已停止 {j} #{n}")
            else:
                print_error(f"停止 {j} #{n} 失败", msg)


def _format_build_info(info: Optional[Dict[str, Any]], job: str, build_num: Optional[int]) -> None:
    """Format and display build information."""
    if info is None:
        print_error("获取构建信息失败", f"未找到 {job} 的构建信息")
        return

    b = info
    p = b["params"]

    ts = b.get("timestamp")
    trigger_time = datetime.datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M:%S") if ts else "Unknown"
    duration_min = b.get("duration", 0) // 60000
    result = b.get("result") or "RUNNING"
    
    status_desc = {
        "SUCCESS": {"icon": "✅", "text": "构建成功"},
        "FAILURE": {"icon": "❌", "text": "构建失败"},
        "ABORTED": {"icon": "■", "text": "已终止"},
        "RUNNING": {"icon": "🔄", "text": "运行中"},
        "NOT_BUILT": {"icon": "⚠️", "text": "未构建"}
    }
    
    status_info = status_desc.get(result, {"icon": "❓", "text": result})

    print(f"[{status_info['icon']} Build #{b['number']}]")
    print(f"状态: {status_info['text']}")
    print(f"触发时间: {trigger_time}")
    print(f"持续时间: {duration_min}min")
    
    if result == "FAILURE":
        print("\n--- 失败原因 ---")
        full_log = get_build_log_tail(job, build_num, LOG_TAIL_LINES) if build_num else ""
        log_lines = full_log.split("\n")
        seen_errors = set()
        
        for i, line in enumerate(log_lines):
            stripped = line.strip()
            if is_noisy_line(line, 15):
                continue
            if any(kw in stripped for kw in ["error:", "ARCHIVE FAILED", "Build Failed", "fatal error", "fatal:"]):
                loc_match = re.search(r"([\w_/\\.]+\.swift):(\d+):\d+:", stripped)
                if loc_match:
                    err_sig = loc_match.group(1) + ":" + loc_match.group(2)
                else:
                    err_sig = stripped[:60]
                if err_sig in seen_errors:
                    continue
                seen_errors.add(err_sig)
                print(f"  {strip_ansi(stripped)}")
                if i + 1 < len(log_lines):
                    next_line = log_lines[i + 1].strip()
                    if not is_noisy_line(next_line, 15) and next_line[:5] not in ("^", ";"):
                        print(f"  {strip_ansi(next_line)}")
    
    elif result == "ABORTED":
        print("\n--- 终止原因 ---")
        abort_reason = info.get("abort_reason", "")
        if abort_reason:
            print(f"  {abort_reason}")
        else:
            full_log = get_build_log_tail(job, build_num, LOG_TAIL_LINES) if build_num else ""
            for line in full_log.split("\n"):
                stripped = line.strip()
                if any(kw in stripped.lower() for kw in ["aborted", "stopped", "terminated"]):
                    if not is_noisy_line(stripped, 10):
                        print(f"  {strip_ansi(stripped)}")
                        break
    
    elif result == "NOT_BUILT":
        abort_reason = info.get("abort_reason", "")
        if abort_reason:
            print("\n--- 未构建原因 ---")
            print(f"  {abort_reason}")
    
    print("\n--- 参数 ---")
    key_params = [
        "flutterModuleBranch", "iOSNativeBranch", "androidNativeBranch",
        "environment", "version", "platform", "uploadTarget",
        "updateNotes", "submitForReview", "isDebug", "needPullBranch"
    ]
    for k in key_params:
        print(f"  {k} = {p.get(k, '')}")
    
    upload_target = p.get("uploadTarget", "")
    if result == "SUCCESS" and upload_target == "pgyer":
        print("\n--- 蒲公英上传 ---")
        full_log = get_build_log_tail(job, build_num, LOG_TAIL_LINES) if build_num else ""
        for line in full_log.split("\n"):
            stripped = line.strip()
            if is_noisy_line(stripped, 8):
                continue
            if any(kw in stripped.lower() for kw in ["pgyer", "buildkey", "buildinfo", "qrcode", "shortcut", "upload", "appurl"]):
                if "pgyer.com/k" in stripped or "upload" in stripped.lower():
                    print(f"  {strip_ansi(stripped)}")
    
    elif result == "SUCCESS" and upload_target == "appleAppStore":
        print("\n--- App Store Connect 上传 ---")
        full_log = get_build_log_tail(job, build_num, LOG_TAIL_LINES) if build_num else ""
        seen_keys = set()
        for line in full_log.split("\n"):
            stripped = line.strip()
            if is_noisy_line(stripped, 10):
                continue
            key = None
            lower = stripped.lower()
            if "successfully uploaded package to app store connect" in lower:
                key = "package_ok"
            elif "finished the upload to app store connect" in lower:
                key = "upload_finished"
            elif "successfully finished processing the build" in lower:
                key = "processing_done"
            if key and key not in seen_keys:
                seen_keys.add(key)
                print(f"  {strip_ansi(stripped)}")
    
    print(f"\n执行 'log-tail {job} {build_num}' 查看最后 {LOG_TAIL_LINES} 行日志")


def cmd_info(job: str, build_num: int) -> None:
    """Display detailed information for a specific build."""
    info = get_build_params(job, build_num)
    _format_build_info(info, job, build_num)


def cmd_last(job: str) -> None:
    """Display information for the last completed build."""
    last = get_last_build(job)
    _format_build_info(last, job, last["number"] if last else None)


def _write_log_file(text: str, suffix: str, job: str, build_num: int) -> str:
    """
    Write log content to a file and return the file path.
    
    Args:
        text: Log content
        suffix: File suffix
        job: Job name
        build_num: Build number
    
    Returns:
        Absolute file path
    """
    log_dir = os.path.expanduser("~/.qclaw/workspace/jenkins-logs")
    os.makedirs(log_dir, exist_ok=True)
    
    filename = f"jenkins_log_{suffix.lstrip('.')}_{job}_{build_num}_{uuid.uuid4().hex[:8]}.txt"
    path = os.path.join(log_dir, filename)
    
    with open(path, "w", encoding="utf-8") as f:
        for line in text.split("\n"):
            stripped = strip_ansi(line.strip())
            if not is_noisy_line(stripped, 1):
                f.write(stripped + "\n")
    
    return path


def cmd_log_tail(job: str, build_num: int, n: Optional[int] = None) -> None:
    """Get the last N lines of console log."""
    _cleanup_old_logs()
    
    if n is None:
        n = LOG_TAIL_LINES
    
    text = get_build_log_tail(job, build_num, n)
    if text.startswith("Failed to fetch log"):
        print_error("获取日志失败", text)
        return
    
    path = _write_log_file(text, ".txt", job, build_num)
    print(path)


def cmd_full_log(job: str, build_num: int) -> None:
    """Get the full console log."""
    _cleanup_old_logs()
    
    text = fetch_build_log(job, build_num)
    if text.startswith("Failed to fetch log"):
        print_error("获取日志失败", text)
        return
    
    path = _write_log_file(text, ".txt", job, build_num)
    print(path)


def _require_default_job() -> str:
    """Require a default job to be configured."""
    if not DEFAULT_JOB:
        print_error("缺少默认 Job", "未指定 job 且 config.json 中未配置 DEFAULT_JOB")
        sys.exit(1)
    return DEFAULT_JOB


def main() -> None:
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Jenkins Build Manager")
        print("用法:")
        print("  python3 jenkins.py status [job...]")
        print("  python3 jenkins.py running [job...]")
        print("  python3 jenkins.py trigger <job> <platform> <env> <flutter> <ios> [android] [isDebug] [upload] [version] [updateNotes] [submitForReview] [needPullBranch]")
        print("  python3 jenkins.py rerun <job> <build_num>")
        print("  python3 jenkins.py rerun-last [job]")
        print("  python3 jenkins.py stop <job> <build_num>")
        print("  python3 jenkins.py stop-running [job...]")
        print("  python3 jenkins.py info <job> <build_num>")
        print("  python3 jenkins.py last [job]")
        print("  python3 jenkins.py log-tail <job> <build_num> [n]")
        print("  python3 jenkins.py full-log <job> <build_num>")
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    try:
        if cmd == "status":
            cmd_status(args if args else [_require_default_job()])

        elif cmd == "running":
            cmd_running(args if args else [_require_default_job()])

        elif cmd == "trigger":
            if len(args) < 5:
                print_error("参数不足", "用法: trigger <job> <platform> <env> <flutter> <ios> [android] [isDebug] [upload] [version] [updateNotes] [submitForReview] [needPullBranch]")
                sys.exit(1)
            
            kw = dict(zip(
                ["job", "platform", "env", "flutter", "ios", "android", "is_debug", "upload",
                 "version", "update_notes", "submit_for_review", "need_pull_branch"],
                args[:12]
            ))
            cmd_trigger(**kw)

        elif cmd == "rerun":
            if len(args) < 2:
                print_error("参数不足", "用法: rerun <job> <build_num>")
                sys.exit(1)
            cmd_rerun(args[0], int(args[1]))

        elif cmd == "rerun-last":
            job = args[0] if args else _require_default_job()
            cmd_rerun_last(job)

        elif cmd == "stop":
            if len(args) < 2:
                print_error("参数不足", "用法: stop <job> <build_num>")
                sys.exit(1)
            cmd_stop(args[0], int(args[1]))

        elif cmd == "stop-running":
            cmd_stop_running(args if args else [_require_default_job()])

        elif cmd == "info":
            if len(args) < 2:
                print_error("参数不足", "用法: info <job> <build_num>")
                sys.exit(1)
            cmd_info(args[0], int(args[1]))

        elif cmd == "last":
            job = args[0] if args else _require_default_job()
            cmd_last(job)

        elif cmd == "log-tail":
            if len(args) < 2:
                print_error("参数不足", "用法: log-tail <job> <build_num> [n]")
                sys.exit(1)
            job = args[0]
            build_num = int(args[1])
            n = int(args[2]) if len(args) > 2 else None
            cmd_log_tail(job, build_num, n)

        elif cmd == "full-log":
            if len(args) < 2:
                print_error("参数不足", "用法: full-log <job> <build_num>")
                sys.exit(1)
            cmd_full_log(args[0], int(args[1]))

        else:
            print_error("未知命令", f"Unknown command: {cmd}")
    
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print_error("执行失败", str(e))
        sys.exit(1)


def _load_evals() -> Dict[str, Any]:
    """Load evaluation configuration from evals.json.
    
    Returns:
        Evaluation configuration dictionary with test cases and feedback rules.
    """
    evals_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "evals.json")
    if not os.path.exists(evals_path):
        return {"tests": [], "feedback_rules": [], "learning_rules": []}
    
    try:
        with open(evals_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"tests": [], "feedback_rules": [], "learning_rules": []}


def _save_evals(config: Dict[str, Any]) -> None:
    """Save evaluation configuration to evals.json."""
    evals_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "evals.json")
    try:
        with open(evals_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print_warning(f"保存评测配置失败: {e}")


def _load_learning_data() -> Dict[str, Any]:
    """Load learning data from a JSON file."""
    data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "learning_data.json")
    if not os.path.exists(data_path):
        return {
            "error_counts": {},
            "success_counts": {},
            "preferred_params": {},
            "last_updated": ""
        }
    
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {
            "error_counts": {},
            "success_counts": {},
            "preferred_params": {},
            "last_updated": ""
        }


def _save_learning_data(data: Dict[str, Any]) -> None:
    """Save learning data to a JSON file."""
    data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "learning_data.json")
    data["last_updated"] = datetime.datetime.now().isoformat()
    try:
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print_warning(f"保存学习数据失败: {e}")


def process_feedback(input_text: str) -> Tuple[str, str]:
    """Process user feedback based on predefined rules.
    
    Args:
        input_text: User feedback text
        
    Returns:
        Tuple of (action, response)
    """
    evals = _load_evals()
    rules = evals.get("feedback_rules", [])
    
    for rule in rules:
        pattern = rule.get("pattern", "")
        action = rule.get("action", "")
        response = rule.get("response", "")
        
        if re.search(pattern, input_text):
            return action, response
    
    return "unknown", ""


def learn_from_error(error_key: str) -> None:
    """Learn from errors and apply auto-fix rules.
    
    Args:
        error_key: Unique identifier for the error
    """
    data = _load_learning_data()
    
    # Increment error count
    data["error_counts"][error_key] = data["error_counts"].get(error_key, 0) + 1
    
    # Check if this error occurs 3 times consecutively
    if data["error_counts"].get(error_key, 0) >= 3:
        print_info(f"检测到错误 '{error_key}' 连续出现3次，应用自动修复规则")
        
        # Apply auto-fix based on error type
        fixes = {
            "platform_missing": {"action": "suggest", "message": "建议设置默认平台为 iOS"},
            "environment_missing": {"action": "suggest", "message": "建议设置默认环境为 test"},
            "android_appstore": {"action": "auto_fix", "message": "自动将 uploadTarget 改为 pgyer"},
            "invalid_platform": {"action": "suggest", "message": "有效的平台值: iOS, Android, all"},
            "invalid_environment": {"action": "suggest", "message": "有效的环境值: test, product, develop, gray, preproduct"}
        }
        
        fix = fixes.get(error_key)
        if fix:
            print_info(f"自动修复: {fix['message']}")
            
            # Update defaults in config
            if fix["action"] == "auto_fix":
                if os.path.exists(_CONFIG_PATH):
                    try:
                        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                        
                        if error_key == "android_appstore":
                            cfg["DEFAULTS"] = cfg.get("DEFAULTS", {})
                            cfg["DEFAULTS"]["uploadTarget"] = "pgyer"
                            
                        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
                            json.dump(cfg, f, indent=2, ensure_ascii=False)
                            
                        print_info("配置已更新")
                    except Exception as e:
                        print_warning(f"更新配置失败: {e}")
    
    _save_learning_data(data)


def learn_preferred_params(params: Dict[str, Any]) -> None:
    """Learn user's preferred parameter combinations.
    
    Args:
        params: Parameters used in a successful operation
    """
    data = _load_learning_data()
    
    # Track preferred parameters
    for key, value in params.items():
        if value and value != "":
            if key not in data["preferred_params"]:
                data["preferred_params"][key] = {}
            data["preferred_params"][key][value] = data["preferred_params"][key].get(value, 0) + 1
    
    _save_learning_data(data)


def suggest_defaults(params: Dict[str, Any]) -> Dict[str, Any]:
    """Suggest default parameters based on learned preferences.
    
    Args:
        params: Current parameters
        
    Returns:
        Parameters with suggested defaults applied
    """
    data = _load_learning_data()
    defaults = {}
    
    for key, values in data["preferred_params"].items():
        if key not in params or not params[key]:
            # Find the most used value
            if values:
                most_used = max(values, key=values.get)
                defaults[key] = most_used
                print_info(f"根据使用习惯，建议 {key}={most_used}")
    
    return defaults


def run_self_test() -> None:
    """Run self-tests based on evaluation configuration."""
    evals = _load_evals()
    tests = evals.get("tests", [])
    
    if not tests:
        print_info("没有配置评测用例")
        return
    
    print("🔍 运行自我检测...")
    passed = 0
    failed = 0
    
    for test in tests:
        test_id = test.get("id", "")
        test_name = test.get("name", "")
        input_params = test.get("input", {})
        expected = test.get("expected", {})
        
        print(f"\n测试: {test_name}")
        
        try:
            cmd = input_params.get("command", "")
            
            if cmd == "trigger":
                params = {
                    "platform": input_params.get("platform", ""),
                    "environment": input_params.get("environment", ""),
                    "uploadTarget": input_params.get("uploadTarget", ""),
                    "isDebug": input_params.get("isDebug", "false")
                }
                
                ok, errors, warnings = validate_params(params.copy())
                success = ok if expected.get("success", True) else not ok
                
                contains = expected.get("contains", [])
                # Combine errors and warnings for checking
                all_messages = errors + warnings
                message = "\n".join(all_messages)
                
                # Check if all expected strings are contained in any message
                all_contained = True
                for c in contains:
                    found = any(c in msg for msg in all_messages)
                    if not found:
                        all_contained = False
                        break
                
                if success and all_contained:
                    print("✅ 通过")
                    passed += 1
                else:
                    print(f"❌ 失败")
                    print(f"   期望: {expected}")
                    print(f"   实际: success={ok}, errors={errors}, warnings={warnings}")
                    failed += 1
                    # Learn from failure
                    if not ok:
                        for error in errors:
                            if "platform 参数不能为空" in error:
                                learn_from_error("platform_missing")
                            elif "environment 参数不能为空" in error:
                                learn_from_error("environment_missing")
                            elif "Android 不支持上传 App Store" in error:
                                learn_from_error("android_appstore")
                            elif "platform 参数值" in error:
                                learn_from_error("invalid_platform")
            
            else:
                print("⚠️ 跳过非验证测试")
                
        except Exception as e:
            print(f"❌ 异常: {e}")
            failed += 1
    
    print(f"\n📊 测试结果: {passed} 通过, {failed} 失败")
    
    if failed > 0:
        print_info("正在分析失败原因并学习...")


def auto_evolve() -> None:
    """Automatically evolve the skill based on learning data."""
    data = _load_learning_data()
    
    print("\n🧠 自我进化分析...")
    
    # Analyze error patterns
    if data["error_counts"]:
        print("错误模式分析:")
        for error, count in sorted(data["error_counts"].items(), key=lambda x: -x[1]):
            print(f"  {error}: {count} 次")
    
    # Analyze preferred parameters
    if data["preferred_params"]:
        print("\n偏好参数分析:")
        for param, values in data["preferred_params"].items():
            if values:
                most_used = max(values, key=values.get)
                print(f"  {param}: {most_used} (使用 {values[most_used]} 次)")
    
    # Suggest improvements
    print("\n💡 改进建议:")
    for error, count in data["error_counts"].items():
        if count >= 2:
            suggestions = {
                "platform_missing": "建议在配置中添加默认平台",
                "environment_missing": "建议在配置中添加默认环境",
                "android_appstore": "建议禁用 Android + appleAppStore 的组合"
            }
            if error in suggestions:
                print(f"  • {suggestions[error]}")


def main() -> None:
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Jenkins Build Manager")
        print("用法:")
        print("  python3 jenkins.py status [job...]")
        print("  python3 jenkins.py running [job...]")
        print("  python3 jenkins.py trigger <job> <platform> <env> <flutter> <ios> [android] [isDebug] [upload] [version] [updateNotes] [submitForReview] [needPullBranch]")
        print("  python3 jenkins.py rerun <job> <build_num>")
        print("  python3 jenkins.py rerun-last [job]")
        print("  python3 jenkins.py stop <job> <build_num>")
        print("  python3 jenkins.py stop-running [job...]")
        print("  python3 jenkins.py info <job> <build_num>")
        print("  python3 jenkins.py last [job]")
        print("  python3 jenkins.py log-tail <job> <build_num> [n]")
        print("  python3 jenkins.py full-log <job> <build_num>")
        print("  python3 jenkins.py self-test")
        print("  python3 jenkins.py evolve")
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # Self-management commands
    if cmd == "self-test":
        run_self_test()
        return
    
    if cmd == "evolve":
        auto_evolve()
        return

    try:
        if cmd == "status":
            cmd_status(args if args else [_require_default_job()])

        elif cmd == "running":
            cmd_running(args if args else [_require_default_job()])

        elif cmd == "trigger":
            if len(args) < 5:
                print_error("参数不足", "用法: trigger <job> <platform> <env> <flutter> <ios> [android] [isDebug] [upload] [version] [updateNotes] [submitForReview] [needPullBranch]")
                learn_from_error("trigger_params_missing")
                sys.exit(1)
            
            kw = dict(zip(
                ["job", "platform", "env", "flutter", "ios", "android", "is_debug", "upload",
                 "version", "update_notes", "submit_for_review", "need_pull_branch"],
                args[:12]
            ))
            
            # Learn preferred params before triggering
            params_to_learn = {
                "platform": kw.get("platform"),
                "environment": kw.get("env"),
                "uploadTarget": kw.get("upload"),
                "isDebug": kw.get("is_debug")
            }
            learn_preferred_params(params_to_learn)
            
            cmd_trigger(**kw)

        elif cmd == "rerun":
            if len(args) < 2:
                print_error("参数不足", "用法: rerun <job> <build_num>")
                sys.exit(1)
            cmd_rerun(args[0], int(args[1]))

        elif cmd == "rerun-last":
            job = args[0] if args else _require_default_job()
            cmd_rerun_last(job)

        elif cmd == "stop":
            if len(args) < 2:
                print_error("参数不足", "用法: stop <job> <build_num>")
                sys.exit(1)
            cmd_stop(args[0], int(args[1]))

        elif cmd == "stop-running":
            cmd_stop_running(args if args else [_require_default_job()])

        elif cmd == "info":
            if len(args) < 2:
                print_error("参数不足", "用法: info <job> <build_num>")
                sys.exit(1)
            cmd_info(args[0], int(args[1]))

        elif cmd == "last":
            job = args[0] if args else _require_default_job()
            cmd_last(job)

        elif cmd == "log-tail":
            if len(args) < 2:
                print_error("参数不足", "用法: log-tail <job> <build_num> [n]")
                sys.exit(1)
            job = args[0]
            build_num = int(args[1])
            n = int(args[2]) if len(args) > 2 else None
            cmd_log_tail(job, build_num, n)

        elif cmd == "full-log":
            if len(args) < 2:
                print_error("参数不足", "用法: full-log <job> <build_num>")
                sys.exit(1)
            cmd_full_log(args[0], int(args[1]))

        else:
            print_error("未知命令", f"Unknown command: {cmd}")
    
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print_error("执行失败", str(e))
        # Learn from exception
        error_key = str(e)[:50]
        learn_from_error(error_key)
        sys.exit(1)


if __name__ == "__main__":
    main()