import json
import os
import subprocess
import urllib.parse
import urllib.request
from typing import Any
from pathlib import Path
from logger import logger
import config

def http_request(
    method: str, 
    url: str, 
    headers: dict = None, 
    body: dict = None,
    timeout: int = 60
) -> tuple[dict, dict]:
    if headers is None:
        headers = {}
    
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers = {**headers, "Content-Type": "application/json"}
    
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            logger.debug(f"HTTP {method} {url} - Status: {resp.status}")
            return payload, dict(resp.headers.items())
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP Error {e.code}: {e.reason}")
        try:
            error_body = e.read().decode("utf-8")
            return {"error": error_body, "status_code": e.code}, {}
        except:
            return {"error": str(e), "status_code": e.code}, {}
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return {"error": str(e)}, {}

def verify_github_token(token: str) -> str | None:
    logger.info(f"Verifying GitHub token...")
    payload, _ = http_request(
        "GET", 
        "https://api.github.com/user", 
        headers={"Authorization": f"Bearer {token}"}
    )
    login = payload.get("login")
    if login:
        logger.info(f"Token verified for user: {login}")
    else:
        logger.warning(f"Token verification failed: {payload.get('error', 'Unknown error')}")
    return login

def get_repo_info(token: str, repo_full_name: str) -> dict | None:
    logger.info(f"Fetching repo info: {repo_full_name}")
    payload, _ = http_request(
        "GET",
        f"https://api.github.com/repos/{repo_full_name}",
        headers={"Authorization": f"Bearer {token}"}
    )
    if payload.get("id"):
        logger.info(f"Repo found: {repo_full_name}")
        return payload
    logger.warning(f"Repo not found: {repo_full_name}")
    return None

def cleanup_temp_files(chat_id: int) -> None:
    try:
        user_tmp = config.TMP_DIR / str(chat_id)
        if user_tmp.exists():
            import shutil
            shutil.rmtree(user_tmp)
            logger.info(f"Cleaned temp files for user {chat_id}")
    except Exception as e:
        logger.error(f"Error cleaning temp files for {chat_id}: {e}")

def sanitize_filename(filename: str) -> str:
    import re
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = filename.replace(' ', '_')
    return filename[:255]

def get_deb_info(deb_path: str) -> dict | None:
    try:
        result = subprocess.run(
            ["dpkg-deb", "-f", deb_path],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            logger.error(f"Failed to read deb info: {result.stderr}")
            return None
        
        info = {}
        for line in result.stdout.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                info[key.strip()] = value.strip()
        
        return info
    except Exception as e:
        logger.error(f"Error reading deb info: {e}")
        return None
