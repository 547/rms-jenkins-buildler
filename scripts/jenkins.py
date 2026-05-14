#!/usr/bin/env python3
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

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "config.json")
_EXAMPLE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "config.json.example")

def _load_config():
    if not os.path.exists(_CONFIG_PATH):
        print("Error: Missing Jenkins config file")
        print("\nPlease configure as follows:")
        print(f"1. Copy template: cp {_EXAMPLE_PATH} {_CONFIG_PATH}")
        print(f"2. Edit {_CONFIG_PATH} with your Jenkins URL, username and API Token")
        print(f"3. Save and run again")
        sys.exit(1)
    
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Config file format error - {e}")
        sys.exit(1)
    
    required_fields = ["JENKINS", "USER", "TOKEN"]
    missing = [f for f in required_fields if f not in cfg or not cfg[f]]
    if missing:
        print(f"Error: Missing required fields in config: {', '.join(missing)}")
        sys.exit(1)
    
    return cfg

_cfg = _load_config()
JENKINS = _cfg["JENKINS"]
USER = _cfg["USER"]
TOKEN = _cfg["TOKEN"]
TIMEOUT = int(_cfg.get("TIMEOUT", 15))
DEFAULT_JOB = _cfg.get("DEFAULT_JOB", "")
DEFAULTS = _cfg.get("DEFAULTS", {})
LOG_TAIL_LINES = int(_cfg.get("logTailLines", 500))

def _cleanup_old_logs(max_age_hours=24):
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
        except Exception:
            pass
    return count

_cleanup_old_logs()

def cred():
    return {"Authorization": "Basic " + base64.b64encode((USER + ":" + TOKEN).encode()).decode()}

def get_crumb():
    req = urllib.request.Request(JENKINS + "/crumbIssuer/api/json", headers=cred())
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)["crumb"]

def api(url, method="GET", data=None, params=None):
    if params:
        sep = "&" if "?" in url else "?"
        url += sep + urllib.parse.urlencode(params)
    crumb = get_crumb()
    headers = {**cred(), "Jenkins-Crumb": crumb}
    if data:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read()
            if r.status in (200, 204, 201):
                result = {"status": "ok", "code": r.status}
                loc = r.headers.get("Location")
                if loc:
                    result["Location"] = loc
                if r.status == 200 and body:
                    try:
                        return {**result, **json.loads(body)}
                    except:
                        pass
                return result
            try:
                return json.loads(body)
            except:
                return {"status": "ok", "text": body.decode(errors="replace")}
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        return {"status": "error", "http": e.code, "body": body[:500]}

def strip_ansi(line):
    return re.sub(r"\x1b\[[0-9;]*m", "", line)

def is_noisy_line(line, min_len=0):
    stripped = line.strip()
    return (
        "ha://" in stripped
        or "[8mha:" in stripped
        or (min_len > 0 and len(stripped) < min_len)
    )

def format_params_for_display(params):
    lines = []
    for key, value in sorted(params.items()):
        val = str(value) if value else ""
        lines.append("  " + key + ": " + val)
    return "\n".join(lines)

def find_running(jobs=None):
    if jobs is None:
        jobs = [DEFAULT_JOB]
    running = []
    for job in jobs:
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

def has_running_build(job=None):
    if job is None:
        job = DEFAULT_JOB
    running = find_running([job])
    return len(running) > 0

def get_builds(job, fields="number,result,building,duration,timestamp,actions[parameters[name,value]]"):
    d = api(f"{JENKINS}/job/{job}/api/json", params={"tree": "builds[" + fields + "]"})
    if d.get("status") == "error":
        return None
    return d.get("builds", [])

def _parse_build(b):
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

def get_build_params(job, build_num):
    builds = get_builds(job, "number,result,building,duration,timestamp,actions[_class,parameters[name,value],causes[shortDescription]]")
    if builds is None:
        return None
    for b in builds:
        if str(b["number"]) == str(build_num):
            return _parse_build(b)
    return None

def get_last_build(job):
    builds = get_builds(job, "number,result,building,duration,timestamp,actions[_class,parameters[name,value],causes[shortDescription]]")
    if builds is None:
        return None
    for b in builds:
        if not b.get("building"):
            return _parse_build(b)
    return None

def fetch_build_log(job, build_num):
    crumb = get_crumb()
    req = urllib.request.Request(
        JENKINS + "/job/" + job + "/" + str(build_num) + "/logText/progressiveText",
        headers={**cred(), "Jenkins-Crumb": crumb},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return "Failed to fetch log: " + str(e)

def get_build_log_tail(job, build_num, n=20):
    text = fetch_build_log(job, build_num)
    if text.startswith("Failed to fetch log"):
        return text
    lines = text.split("\n")
    return "\n".join(lines[-n:])

def apply_smart_defaults(params):
    u = params.get("uploadTarget", "")
    s = params.get("submitForReview", "false")
    
    if u == "appleAppStore":
        params["platform"] = "iOS"
        params["environment"] = "product"
    
    if s == "true":
        params["submitForReview"] = "true"
        params["platform"] = "iOS"
        params["environment"] = "product"
        params["uploadTarget"] = "appleAppStore"
    
    return params

def validate_params(params):
    errors = []
    warnings = []
    p = params.get("platform", "")
    e = params.get("environment", "")
    u = params.get("uploadTarget", "")
    vd = params.get("isDebug", "false")

    if not p:
        errors.append("platform parameter cannot be empty")
    if not e:
        errors.append("environment parameter cannot be empty")
    
    if p in ("Android", "all") and e in ("develop", "gray"):
        params["environment"] = "test"
        warnings.append("Android does not support " + e + " environment, downgraded to test")

    if u == "appleAppStore" and p == "Android":
        errors.append("Android does not support uploading to App Store")

    if vd == "true" and p not in ("Android", "all"):
        errors.append("isDebug=true is only valid for Android")

    return len(errors) == 0, errors, warnings

def trigger(job, **kwargs):
    params = dict(DEFAULTS)
    for k, v in kwargs.items():
        if v is not None and v != "":
            params[k] = v
    
    params = apply_smart_defaults(params)
    
    ok, errors, warnings = validate_params(params)
    if not ok:
        return False, "\n".join(errors), None, params
    
    running_list = find_running([job])
    if running_list:
        running_info = []
        for j, n, r_params in running_list:
            running_info.append("  Job: " + j)
            running_info.append("  Build #: #" + str(n))
            running_info.append("  Params:")
            running_info.append(format_params_for_display(r_params))
        message = "Found running jobs:\n" + chr(10).join(running_info) + "\n\nStarting new job will terminate current job, continue?"
        return False, message, None, params
    
    result = api(JENKINS + "/job/" + job + "/buildWithParameters", method="POST", data=params)
    if result.get("status") == "error":
        return False, "API Error HTTP " + str(result.get('http')) + ": " + str(result.get('body','')[:200]), None, params

    loc = result.get("Location", "")
    if not loc:
        return True, "ok", None, params

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

def _poll_build_num_from_queue(queue_url, max_wait=10):
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
        except Exception:
            continue
    print("Warning: Polled " + str(max_wait) + "s but still no build number", file=sys.stderr)
    return None

def stop(job, build_num):
    result = api(JENKINS + "/job/" + job + "/" + str(build_num) + "/stop", method="POST")
    if result.get("status") == "error":
        return False, "HTTP " + str(result.get('http')) + ": " + str(result.get('body','')[:200])
    return True, "ok"

def stop_all(jobs=None):
    if jobs is None:
        jobs = [DEFAULT_JOB]
    results = []
    for job in jobs:
        for j, n, _ in find_running([job]):
            ok, msg = stop(j, n)
            results.append((j, n, ok, msg))
    return results

def rerun(job, build_num):
    info = get_build_params(job, build_num)
    if info is None:
        return False, "Cannot find params for " + job + " #" + str(build_num), None, {}
    if info.get("building"):
        return False, job + " #" + str(build_num) + " is still running, please stop first", None, {}

    params = info["params"]
    ok, msg, new_build, _ = trigger(job, **params)
    if not ok:
        return False, msg, None, params
    return True, msg, new_build, params

def cmd_status(jobs):
    for job in jobs:
        builds = get_builds(job)
        if builds is None:
            print("Error: " + job + ": Cannot get status")
            continue
        running_list = [(b["number"], b.get("duration", 0) // 60000, _get_build_params_from_build(b))
                        for b in builds if b.get("building")]
        last = next((b for b in builds if not b.get("building")), None)
        print("\n[" + job + "]")
        if running_list:
            for n, dur, params in running_list:
                print("  Running: #" + str(n) + " (" + str(dur) + "min)")
                if params:
                    print("    Params: " + format_params_for_display(params))
        else:
            print("  No running jobs")
        if last:
            r = last.get("result") or "SUCCESS"
            icon = "OK" if r == "SUCCESS" else ("FAIL" if r == "FAILURE" else ("ABORTED" if r == "ABORTED" else "?"))
            print("  Last: #" + str(last['number']) + " " + icon + " " + r + " (" + str(last.get('duration',0)//60000) + "min)")

def _get_build_params_from_build(b):
    params = {}
    for a in b.get("actions", []):
        if "parameters" in a:
            for p in a["parameters"]:
                params[p["name"]] = p["value"]
    return params

def cmd_running(jobs):
    found = find_running(jobs)
    if not found:
        print("NONE")
    else:
        for j, n, params in found:
            params_str = ",".join([k + "=" + str(v) for k, v in params.items()])
            print(j + "|" + str(n) + "|" + params_str)

def cmd_trigger(job, platform=None, env=None, flutter=None, ios=None, android="master",
                is_debug="false", upload="pgyer", version="", update_notes="",
                submit_for_review="false", need_pull_branch="true"):
    params = {
        "platform": platform, "environment": env,
        "flutterModuleBranch": flutter, "iOSNativeBranch": ios,
        "androidNativeBranch": android,
        "uploadTarget": upload, "isDebug": is_debug,
        "version": version, "updateNotes": update_notes,
        "submitForReview": submit_for_review,
        "needPullBranch": need_pull_branch,
    }
    
    if not platform:
        print("Error: platform parameter cannot be empty")
        return
    if not env:
        print("Error: environment parameter cannot be empty")
        return
    
    ok, msg, build_num, final_params = trigger(job, **params)
    
    if not ok:
        if "Found running jobs" in msg:
            print(msg)
        else:
            print("Error: " + msg)
        return
    
    print("Triggered " + job + " #" + str(build_num))
    print("\nBuild Parameters:")
    print(format_params_for_display(final_params))

def cmd_rerun(job, build_num):
    ok, msg, new_build, params = rerun(job, build_num)
    if not ok:
        if "Found running jobs" in msg:
            print(msg)
        else:
            print("Error: " + msg)
        return
    
    print("Rerunning " + job + " #" + str(build_num))
    if new_build:
        print("  New build #: #" + str(new_build))
    print("\nBuild Parameters:")
    print(format_params_for_display(params))

def cmd_rerun_last(job):
    last = get_last_build(job)
    if last is None:
        print("Error: No history builds found for " + job)
        return
    
    ok, msg, new_build, params = rerun(job, last["number"])
    if not ok:
        if "Found running jobs" in msg:
            print(msg)
        else:
            print("Error: " + msg)
        return
    
    print("Rerunning " + job + " #" + str(last["number"]))
    if new_build:
        print("  New build #: #" + str(new_build))
    print("\nBuild Parameters:")
    print(format_params_for_display(params))

def cmd_stop(job, build_num):
    ok, msg = stop(job, build_num)
    if not ok:
        print("Error: " + msg)
    else:
        print("Stopped " + job + " #" + str(build_num))

def cmd_stop_running(jobs):
    results = stop_all(jobs)
    if not results:
        print("No running jobs")
    else:
        for j, n, ok, msg in results:
            if ok:
                print("Stopped " + j + " #" + str(n))
            else:
                print("Failed to stop " + j + " #" + str(n) + ": " + msg)

def _format_build_info(info, job, build_num):
    if info is None:
        print("Error: No build found for " + job)
        return

    b = info
    p = b["params"]

    ts = b.get("timestamp")
    trigger_time = datetime.datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M:%S") if ts else "Unknown"
    duration_min = b.get("duration", 0) // 60000
    result = b.get("result") or "RUNNING"
    status_desc = {
        "SUCCESS": "SUCCESS",
        "FAILURE": "FAILURE",
        "ABORTED": "ABORTED",
        "RUNNING": "RUNNING",
        "NOT_BUILT": "NOT_BUILT"
    }

    print("[Build #" + str(b['number']) + "]")
    print("Status: " + status_desc.get(result, result))
    print("Trigger Time: " + trigger_time)
    print("Duration: " + str(duration_min) + "min")
    
    if result == "FAILURE":
        print("\n--- Failure Reason ---")
        full_log = get_build_log_tail(job, build_num, LOG_TAIL_LINES)
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
                print("  " + strip_ansi(stripped))
                if i + 1 < len(log_lines):
                    next_line = log_lines[i + 1].strip()
                    if not is_noisy_line(next_line, 15) and next_line[:5] not in ("^", ";"):
                        print("  " + strip_ansi(next_line))
    
    elif result == "ABORTED":
        print("\n--- Abort Reason ---")
        abort_reason = info.get("abort_reason", "")
        if abort_reason:
            print("  " + abort_reason)
        else:
            full_log = get_build_log_tail(job, build_num, LOG_TAIL_LINES)
            for line in full_log.split("\n"):
                stripped = line.strip()
                if any(kw in stripped.lower() for kw in ["aborted", "stopped", "terminated"]):
                    if not is_noisy_line(stripped, 10):
                        print("  " + strip_ansi(stripped))
                        break
    
    elif result == "NOT_BUILT":
        abort_reason = info.get("abort_reason", "")
        if abort_reason:
            print("\n--- Abort Reason ---")
            print("  " + abort_reason)
    
    print("\n--- Parameters ---")
    key_params = [
        "flutterModuleBranch", "iOSNativeBranch", "androidNativeBranch",
        "environment", "version", "platform", "uploadTarget",
        "updateNotes", "submitForReview", "isDebug", "needPullBranch"
    ]
    for k in key_params:
        print("  " + k + " = " + str(p.get(k, "")))
    
    upload_target = p.get("uploadTarget", "")
    if result == "SUCCESS" and upload_target == "pgyer":
        print("\n--- Pgyer Upload ---")
        full_log = get_build_log_tail(job, build_num, LOG_TAIL_LINES)
        for line in full_log.split("\n"):
            stripped = line.strip()
            if is_noisy_line(stripped, 8):
                continue
            if any(kw in stripped.lower() for kw in ["pgyer", "buildkey", "buildinfo", "qrcode", "shortcut", "upload", "appurl"]):
                if "pgyer.com/k" in stripped or "upload" in stripped.lower():
                    print("  " + strip_ansi(stripped))
    
    elif result == "SUCCESS" and upload_target == "appleAppStore":
        print("\n--- App Store Connect Upload ---")
        full_log = get_build_log_tail(job, build_num, LOG_TAIL_LINES)
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
                print("  " + strip_ansi(stripped))
    
    print("\nType 'log-tail' to get last 500 lines of console log")

def cmd_info(job, build_num):
    info = get_build_params(job, build_num)
    _format_build_info(info, job, build_num)

def cmd_last(job):
    last = get_last_build(job)
    _format_build_info(last, job, last["number"] if last else None)

def _write_log_file(text, suffix, job, build_num):
    log_dir = os.path.expanduser("~/.qclaw/workspace/jenkins-logs")
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, "jenkins_log_" + suffix.lstrip('.') + "_" + job + "_" + str(build_num) + "_" + uuid.uuid4().hex[:8] + ".txt")
    with open(path, "w", encoding="utf-8") as f:
        for line in text.split("\n"):
            stripped = strip_ansi(line.strip())
            if not is_noisy_line(stripped, 1):
                f.write(stripped + "\n")
    return path

def cmd_log_tail(job, build_num, n=None):
    _cleanup_old_logs()
    if n is None:
        n = LOG_TAIL_LINES
    text = get_build_log_tail(job, build_num, n)
    if text.startswith("Failed to fetch log"):
        print(text)
        return
    path = _write_log_file(text, ".txt", job, build_num)
    print(path)

def cmd_full_log(job, build_num):
    _cleanup_old_logs()
    text = fetch_build_log(job, build_num)
    if text.startswith("Failed to fetch log"):
        print(text)
        return
    path = _write_log_file(text, ".txt", job, build_num)
    print(path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Jenkins Build Manager")
        print("Usage:")
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
    default_job = DEFAULT_JOB

    def _require_default_job():
        if not default_job:
            print("Error: No job specified and DEFAULT_JOB not configured in config.json")
            sys.exit(1)
        return default_job

    if cmd == "status":
        cmd_status(args if args else [_require_default_job()])

    elif cmd == "running":
        cmd_running(args if args else [_require_default_job()])

    elif cmd == "trigger":
        if len(args) < 5:
            print("Usage: trigger <job> <platform> <env> <flutter> <ios> [android] [isDebug] [upload] [version] [updateNotes] [submitForReview] [needPullBranch]")
            sys.exit(1)
        kw = dict(zip(
            ["job","platform","env","flutter","ios","android","is_debug","upload",
             "version","update_notes","submit_for_review","need_pull_branch"],
            args[:12]
        ))
        cmd_trigger(**kw)

    elif cmd == "rerun":
        if len(args) < 2:
            print("Usage: rerun <job> <build_num>")
            sys.exit(1)
        cmd_rerun(args[0], args[1])

    elif cmd == "rerun-last":
        if not args:
            args = [_require_default_job()]
        cmd_rerun_last(args[0])

    elif cmd == "stop":
        if len(args) < 2:
            print("Usage: stop <job> <build_num>")
            sys.exit(1)
        cmd_stop(args[0], args[1])

    elif cmd == "stop-running":
        cmd_stop_running(args if args else [_require_default_job()])

    elif cmd == "info":
        if len(args) < 2:
            print("Usage: info <job> <build_num>")
            sys.exit(1)
        cmd_info(args[0], args[1])

    elif cmd == "last":
        job = args[0] if args else _require_default_job()
        cmd_last(job)

    elif cmd == "log-tail":
        if len(args) < 2:
            print("Usage: log-tail <job> <build_num> [n]")
            sys.exit(1)
        job = args[0]
        build_num = args[1]
        n = int(args[2]) if len(args) > 2 else None
        cmd_log_tail(job, build_num, n)

    elif cmd == "full-log":
        if len(args) < 2:
            print("Usage: full-log <job> <build_num>")
            sys.exit(1)
        cmd_full_log(args[0], args[1])

    else:
        print("Unknown command: " + cmd)
