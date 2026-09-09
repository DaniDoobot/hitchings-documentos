#!/usr/bin/env python3
"""
smoke_docker_local.py — Smoke test para la imagen Docker local de HITCHINGS.

Prerrequisitos:
    docker compose -f docker-compose.local.yml up -d --build
    (esperar a que el healthcheck del backend pase)

Uso:
    python scripts/smoke_docker_local.py [--base-url URL] [--user USER] [--password PASS]

Por defecto usa:
    URL:      http://127.0.0.1:8080
    Usuario:  hitchings  (o APP_BASIC_AUTH_USER del entorno)
    Password: test1234   (o APP_BASIC_AUTH_PASSWORD del entorno)
"""

import argparse
import base64
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

# ----------------------------------------------------------------
# Configuración por defecto
# ----------------------------------------------------------------
DEFAULT_BASE_URL = "http://127.0.0.1:8080"
DEFAULT_USER     = os.environ.get("APP_BASIC_AUTH_USER", "hitchings")
DEFAULT_PASSWORD = os.environ.get("APP_BASIC_AUTH_PASSWORD", "test1234")

PASS = "\033[92m✔ PASS\033[0m"
FAIL = "\033[91m✖ FAIL\033[0m"


def _auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def _request(url: str, method: str = "GET", headers: dict | None = None,
             data: bytes | None = None, expect_status: int | None = None,
             timeout: int = 10) -> tuple[int, bytes, dict]:
    req = urllib.request.Request(url, method=method, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        body = e.read()
        return e.code, body, dict(e.headers)


def check(label: str, ok: bool, detail: str = "") -> bool:
    status = PASS if ok else FAIL
    line = f"  {status}  {label}"
    if detail:
        line += f"\n         {detail}"
    print(line)
    return ok


def run_smoke(base_url: str, user: str, password: str) -> int:
    auth = _auth_header(user, password)
    failures = 0

    print(f"\n{'='*60}")
    print(f"  HITCHINGS Documentos — Smoke Test Docker Local")
    print(f"  URL base : {base_url}")
    print(f"  Usuario  : {user}")
    print(f"{'='*60}\n")

    # 1. Sin credenciales → 401
    status, _, _ = _request(base_url + "/")
    ok = (status == 401)
    if not check("GET / sin credenciales → 401", ok, f"status={status}"):
        failures += 1

    # 2. /healthz sin credenciales → 200
    status, body, _ = _request(base_url + "/healthz")
    ok = (status == 200 and b"ok" in body.lower())
    if not check("GET /healthz sin credenciales → 200", ok, f"status={status}, body={body[:50]}"):
        failures += 1

    # 3. Con credenciales → 200
    status, _, _ = _request(base_url + "/", headers={"Authorization": auth})
    ok = (status == 200)
    if not check("GET / con credenciales → 200", ok, f"status={status}"):
        failures += 1

    # 4. SPA fallback — ruta inexistente con auth → 200 + HTML
    status, body, headers = _request(
        base_url + "/ruta-inexistente-spa",
        headers={"Authorization": auth}
    )
    ok = (status == 200 and b"<!doctype html" in body.lower())
    if not check("SPA fallback /ruta-inexistente-spa → 200 + HTML", ok,
                 f"status={status}, content-type={headers.get('Content-Type', '?')}"):
        failures += 1

    # 5. /api/v1/prompts con auth → JSON con lista de prompts
    status, body, headers = _request(
        base_url + "/api/v1/prompts",
        headers={"Authorization": auth, "Accept": "application/json"}
    )
    try:
        data = json.loads(body)
        ok = (status == 200 and isinstance(data, list) and len(data) > 0)
        detail = f"status={status}, prompts={len(data)}"
    except Exception as e:
        ok = False
        detail = f"status={status}, json parse error: {e}"
    if not check("GET /api/v1/prompts → 200 + lista JSON", ok, detail):
        failures += 1

    # 6. POST /api/v1/text/prepare con auth → 200
    payload = json.dumps({
        "text": "Texto de prueba del smoke test de Docker local."
    }).encode()
    status, body, _ = _request(
        base_url + "/api/v1/text/prepare",
        method="POST",
        headers={
            "Authorization": auth,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        data=payload,
    )
    ok = (status == 200)
    if not check("POST /api/v1/text/prepare → 200", ok, f"status={status}"):
        failures += 1

    # 7. Puerto 8000 del backend NO accesible desde el host
    try:
        s = socket.create_connection(("127.0.0.1", 8000), timeout=3)
        s.close()
        backend_accessible = True
    except (ConnectionRefusedError, OSError):
        backend_accessible = False
    ok = not backend_accessible
    if not check("Puerto 8000 backend NO accesible en host", ok,
                 "PROBLEMA: el puerto 8000 está expuesto al host" if not ok else ""):
        failures += 1

    # 8. Cabeceras de seguridad presentes
    _, _, headers = _request(base_url + "/", headers={"Authorization": auth})
    required_headers = [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
    ]
    for h in required_headers:
        found = any(k.lower() == h.lower() for k in headers)
        if not check(f"Cabecera de seguridad: {h}", found,
                     f"Cabeceras recibidas: {list(headers.keys())[:8]}"):
            failures += 1

    # 9. Sin localhost:8000 en el bundle del frontend
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        count = 0
        for f in frontend_dist.rglob("*"):
            if f.is_file() and f.suffix in {".js", ".html", ".css"}:
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    if "localhost:8000" in content:
                        count += 1
                except Exception:
                    pass
        ok = (count == 0)
        if not check(
            f"Sin referencias a localhost:8000 en frontend/dist/",
            ok,
            f"Encontradas {count} ocurrencias" if not ok else ""
        ):
            failures += 1
    else:
        print(f"  ⚠ SKIP  Sin localhost:8000 en dist/ (dist/ no existe localmente)")

    # 10. Sin GEMINI_API_KEY en el bundle
    if frontend_dist.exists():
        count = 0
        for f in frontend_dist.rglob("*"):
            if f.is_file() and f.suffix in {".js", ".html", ".css"}:
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    if "GEMINI_API_KEY" in content:
                        count += 1
                except Exception:
                    pass
        ok = (count == 0)
        if not check(
            "Sin GEMINI_API_KEY en frontend/dist/",
            ok,
            f"Encontradas {count} ocurrencias — PROBLEMA DE SEGURIDAD" if not ok else ""
        ):
            failures += 1
    else:
        print(f"  ⚠ SKIP  Sin GEMINI_API_KEY en dist/ (dist/ no existe localmente)")

    # ----------------------------------------------------------------
    print(f"\n{'='*60}")
    if failures == 0:
        print(f"  \033[92m✔ Todos los checks pasaron correctamente.\033[0m")
    else:
        print(f"  \033[91m✖ {failures} check(s) fallaron.\033[0m")
    print(f"{'='*60}\n")

    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test Docker local HITCHINGS")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--user",     default=DEFAULT_USER)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    args = parser.parse_args()

    failures = run_smoke(args.base_url, args.user, args.password)
    sys.exit(failures)


if __name__ == "__main__":
    main()
