#!/usr/bin/env python3
"""Comet Smoke Test & Auto-Recovery
Local: /opt/comet-tools/smoke.py
Interpretador: /opt/comet/.venv/bin/python
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
import httpx

COMET_DIR = Path("/opt/comet")
COMET_CODE_DIR = COMET_DIR / "comet"
DATA_DIR = COMET_DIR / "data"
ENV_PATH = COMET_DIR / ".env"
LAST_GOOD_TAR = DATA_DIR / "last_good.tar.gz"
LAST_GOOD_SHA1 = DATA_DIR / "last_good.sha1"
SMOKE_LAST_JSON = DATA_DIR / "smoke_last.json"
SMOKE_DISABLE = DATA_DIR / "smoke.disable"

LOCAL_BASE_URL = "http://127.0.0.1:8000"


def load_env() -> dict:
    env = {}
    if not ENV_PATH.is_file():
        return env
    try:
        content = ENV_PATH.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env


def rewrite_url(url: str, public_base: str, local_base: str = LOCAL_BASE_URL) -> str:
    if public_base and url.startswith(public_base):
        rel = url[len(public_base):]
        if not rel.startswith("/") and not local_base.endswith("/"):
            return local_base + "/" + rel
        if rel.startswith("/") and local_base.endswith("/"):
            return local_base + rel[1:]
        return local_base + rel
    return url


def compute_code_hash(fake_changed: bool = False) -> str:
    hasher = hashlib.sha1()
    if not COMET_CODE_DIR.exists():
        return ""
    py_files = sorted(
        p for p in COMET_CODE_DIR.rglob("*.py")
        if "__pycache__" not in p.parts
    )
    tpl_file = COMET_CODE_DIR / "templates" / "index.html"
    files = list(py_files)
    if tpl_file.is_file():
        files.append(tpl_file)
    files.sort()

    for f in files:
        try:
            rel = f.relative_to(COMET_CODE_DIR).as_posix()
            hasher.update(rel.encode("utf-8") + b"\0")
            hasher.update(f.read_bytes())
        except Exception:
            pass

    digest = hasher.hexdigest()
    if fake_changed or os.environ.get("SMOKE_FAKE_CHANGED") == "1":
        digest += "-fake-changed"
    return digest


def create_snapshot(current_hash: str):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp_tar = DATA_DIR / "last_good.tar.gz.tmp"
    with tarfile.open(tmp_tar, "w:gz") as tar:
        def filter_pycache(tarinfo):
            if "__pycache__" in tarinfo.name or tarinfo.name.endswith(".pyc"):
                return None
            return tarinfo
        tar.add(str(COMET_CODE_DIR), arcname="comet", filter=filter_pycache)
    tmp_tar.replace(LAST_GOOD_TAR)
    LAST_GOOD_SHA1.write_text(current_hash, encoding="utf-8")


def restore_snapshot() -> bool:
    if not LAST_GOOD_TAR.is_file():
        return False
    if COMET_CODE_DIR.exists():
        shutil.rmtree(COMET_CODE_DIR)
    with tarfile.open(LAST_GOOD_TAR, "r:gz") as tar:
        if hasattr(tarfile, 'data_filter'):
            tar.extractall(path=str(COMET_DIR), filter='data')
        else:
            tar.extractall(path=str(COMET_DIR))
    return True


def restart_comet(token: str) -> bool:
    subprocess.run(["pkill", "-9", "-f", "python -m comet.main"], check=False)
    time.sleep(1)

    log_file = Path("/var/tmp/comet.log")
    try:
        log_fd = open(log_file, "a")
    except Exception:
        log_fd = subprocess.DEVNULL

    subprocess.Popen(
        ["/opt/comet/.venv/bin/python", "-m", "comet.main"],
        cwd=str(COMET_DIR),
        stdout=log_fd,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )

    start_wait = time.time()
    while time.time() - start_wait < 35:
        time.sleep(1)
        try:
            r = httpx.get(f"{LOCAL_BASE_URL}/{token}/manifest.json", timeout=3.0)
            if r.status_code == 200:
                return True
        except Exception:
            pass
    return False


def send_notification(ntfy_topic: str, failed_names: list, restored: bool):
    if not ntfy_topic:
        return
    text = f"Comet: SMOKE FALHOU ({', '.join(failed_names)})"
    if restored:
        text += " - restaurado para a última versão boa"
    try:
        httpx.post(f"https://ntfy.sh/{ntfy_topic}", content=text.encode("utf-8"), timeout=10.0)
    except Exception:
        pass


def check_manifest(client: httpx.Client, token: str, force_fail: bool) -> tuple:
    if force_fail or os.environ.get("SMOKE_FORCE_FAIL") == "1":
        return False, "falha forçada por SMOKE_FORCE_FAIL"

    start_wait = time.time()
    last_err = ""
    while time.time() - start_wait < 35:
        try:
            r = client.get(f"/{token}/manifest.json", timeout=15.0)
            if r.status_code != 200:
                return False, f"status {r.status_code}"
            data = r.json()
            cats = data.get("catalogs", [])
            count = len(cats)
            if count >= 40:
                return True, f"{count} catálogos"
            else:
                return False, f"esperado >= 40 catálogos, obtido {count}"
        except httpx.ConnectError:
            time.sleep(1)
            last_err = "conexão recusada (servidor iniciando)"
        except Exception as e:
            time.sleep(1)
            last_err = str(e)
    return False, f"tempo esgotado aguardando Comet ({last_err})"


def check_catalogos(client: httpx.Client, token: str, public_base: str) -> tuple:
    target_cats = [
        "catalog/movie/comet_top10",
        "catalog/series/comet_top10",
        "catalog/movie/comet_trending",
        "catalog/series/comet_trending"
    ]
    for cat in target_cats:
        url = f"/{token}/{cat}.json"
        try:
            r = client.get(url, timeout=20.0)
        except Exception as e:
            return False, f"{cat}: erro na requisição: {e}"
        if r.status_code != 200:
            return False, f"{cat}: status {r.status_code}"

        try:
            data = r.json()
        except Exception:
            return False, f"{cat}: resposta não é json válido"

        metas = data.get("metas", [])
        if len(metas) < 5:
            return False, f"{cat}: esperado >= 5 metas, obtido {len(metas)}"

        for idx, m in enumerate(metas):
            p = m.get("poster", "")
            if not isinstance(p, str) or not (p.startswith("http://") or p.startswith("https://")):
                return False, f"{cat}: meta[{idx}] poster inválido"

        first_poster = metas[0].get("poster", "")
        img_url = rewrite_url(first_poster, public_base)
        try:
            with httpx.Client(follow_redirects=True, timeout=10.0) as img_client:
                r_img = img_client.get(img_url, headers={"Range": "bytes=0-1023"})
                if r_img.status_code not in (200, 206):
                    return False, f"{cat}: poster status {r_img.status_code}"
                ct = r_img.headers.get("content-type", "").lower()
                if not ct.startswith("image/"):
                    return False, f"{cat}: poster content-type '{ct}' não é image/*"
        except Exception as e:
            return False, f"{cat}: erro ao acessar poster: {e}"

    return True, "4 catálogos verificados"


def check_stream_filme(client: httpx.Client, token: str) -> tuple:
    url = f"/{token}/stream/movie/tt12042730.json"
    t0 = time.time()
    try:
        r = client.get(url, timeout=40.0)
    except httpx.TimeoutException:
        return False, "tempo esgotado (> 40s)", {}
    except Exception as e:
        return False, f"erro na requisição: {e}", {}

    elapsed = time.time() - t0
    if elapsed > 40.0:
        return False, f"tempo excedido ({elapsed:.1f}s > 40s)", {}

    if r.status_code != 200:
        return False, f"status {r.status_code}", {}

    try:
        data = r.json()
    except Exception:
        return False, "resposta não é json válido", {}

    streams = data.get("streams", [])
    if len(streams) < 20:
        return False, f"esperado >= 20 streams, obtido {len(streams)}", {}

    first = streams[0]
    name = first.get("name", "")
    if not name.startswith("▶ Assistir"):
        return False, "1º stream name não começa com '▶ Assistir'", {}

    return True, f"{len(streams)} streams, 1º '▶ Assistir'", first


def check_stream_serie(client: httpx.Client, token: str) -> tuple:
    url = f"/{token}/stream/series/tt0903747:1:1.json"
    t0 = time.time()
    try:
        r = client.get(url, timeout=40.0)
    except httpx.TimeoutException:
        return False, "tempo esgotado (> 40s)"
    except Exception as e:
        return False, f"erro na requisição: {e}"

    elapsed = time.time() - t0
    if elapsed > 40.0:
        return False, f"tempo excedido ({elapsed:.1f}s > 40s)"

    if r.status_code != 200:
        return False, f"status {r.status_code}"

    try:
        data = r.json()
    except Exception:
        return False, "resposta não é json válido"

    streams = data.get("streams", [])
    if len(streams) < 20:
        return False, f"esperado >= 20 streams, obtido {len(streams)}"

    return True, f"{len(streams)} streams"


def check_play(first_stream: dict, public_base: str) -> tuple:
    stream_url = first_stream.get("url", "")
    if not stream_url:
        return False, "nenhuma url no 1º stream"

    play_url = rewrite_url(stream_url, public_base)
    headers = {
        "User-Agent": "ExoPlayerLib/2.19.1",
        "Range": "bytes=0-1023"
    }
    t0 = time.time()
    try:
        with httpx.Client(follow_redirects=True, max_redirects=8, timeout=20.0) as play_client:
            r = play_client.get(play_url, headers=headers)
    except httpx.TimeoutException:
        return False, "tempo esgotado (> 20s)"
    except Exception as e:
        return False, f"erro ao acessar stream: {e}"

    elapsed = time.time() - t0
    if elapsed > 20.0:
        return False, f"tempo excedido ({elapsed:.1f}s > 20s)"

    if r.status_code not in (200, 206):
        return False, f"status {r.status_code}"

    ct = r.headers.get("content-type", "").lower()
    url_str = str(r.url).lower()
    is_video = ct.startswith("video/")
    is_octet = ct.startswith("application/octet-stream")
    is_hls = "mpegurl" in ct or ".m3u8" in url_str

    if is_video or is_octet or is_hls:
        kind = "video" if is_video else ("hls" if is_hls else "octet-stream")
        return True, f"status {r.status_code}, {kind} ({ct})"

    return False, f"content-type incompatível: {ct}"


def check_log(log_file_path: Path, log_offset: int) -> tuple:
    if not log_file_path.is_file():
        alt = Path("/var/tmp/smoke_log.txt")
        if alt.is_file():
            log_file_path = alt
            log_offset = 0
        else:
            return True, "0 erros (log não encontrado)"

    try:
        with open(log_file_path, "r", encoding="utf-8", errors="replace") as f:
            if log_offset > 0:
                f.seek(log_offset)
            content = f.read()

        if log_file_path != Path("/var/tmp/smoke_log.txt"):
            try:
                Path("/var/tmp/smoke_log.txt").write_text(content, encoding="utf-8")
            except Exception:
                pass

        errors = []
        if "Traceback" in content:
            errors.append("Traceback")
        if "NameError" in content:
            errors.append("NameError")
        if errors:
            return False, f"erros detectados: {', '.join(errors)}"
        return True, "0 erros no log"
    except Exception as e:
        return False, f"erro ao ler log: {e}"


def run_all_checks(client: httpx.Client, token: str, public_base: str, log_path: Path, log_offset: int, force_fail: bool) -> tuple:
    results = []

    # 1. manifest
    t0 = time.time()
    ok1, why1 = check_manifest(client, token, force_fail)
    s1 = time.time() - t0
    results.append({"name": "manifest", "ok": ok1, "why": why1, "secs": round(s1, 2)})
    print(f"manifest: {'OK' if ok1 else 'FALHA'} ({why1}) [{s1:.2f}s]")

    # 2. catalogos
    t0 = time.time()
    ok2, why2 = check_catalogos(client, token, public_base)
    s2 = time.time() - t0
    results.append({"name": "catalogos", "ok": ok2, "why": why2, "secs": round(s2, 2)})
    print(f"catalogos: {'OK' if ok2 else 'FALHA'} ({why2}) [{s2:.2f}s]")

    # 3. stream_filme
    t0 = time.time()
    ok3, why3, first_stream = check_stream_filme(client, token)
    s3 = time.time() - t0
    results.append({"name": "stream_filme", "ok": ok3, "why": why3, "secs": round(s3, 2)})
    print(f"stream_filme: {'OK' if ok3 else 'FALHA'} ({why3}) [{s3:.2f}s]")

    # 4. stream_serie
    t0 = time.time()
    ok4, why4 = check_stream_serie(client, token)
    s4 = time.time() - t0
    results.append({"name": "stream_serie", "ok": ok4, "why": why4, "secs": round(s4, 2)})
    print(f"stream_serie: {'OK' if ok4 else 'FALHA'} ({why4}) [{s4:.2f}s]")

    # 5. play
    t0 = time.time()
    if ok3 and first_stream:
        ok5, why5 = check_play(first_stream, public_base)
    else:
        ok5, why5 = False, "pulado (stream_filme falhou)"
    s5 = time.time() - t0
    results.append({"name": "play", "ok": ok5, "why": why5, "secs": round(s5, 2)})
    print(f"play: {'OK' if ok5 else 'FALHA'} ({why5}) [{s5:.2f}s]")

    # 6. log
    t0 = time.time()
    ok6, why6 = check_log(log_path, log_offset)
    s6 = time.time() - t0
    results.append({"name": "log", "ok": ok6, "why": why6, "secs": round(s6, 2)})
    print(f"log: {'OK' if ok6 else 'FALHA'} ({why6}) [{s6:.2f}s]")

    all_ok = all(r["ok"] for r in results)
    return results, all_ok, first_stream


def save_smoke_last(results: list, all_ok: bool):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "ok": all_ok,
        "checks": results
    }
    try:
        SMOKE_LAST_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Comet Smoke Test & Recovery")
    parser.add_argument("--log-file", default="/var/tmp/comet.log", help="Caminho do log")
    parser.add_argument("--log-offset", type=int, default=0, help="Offset inicial em bytes")
    parser.add_argument("--check-log", help="Apenas verifica arquivo de log")
    parser.add_argument("--force-fail", action="store_true", help="Força falha do manifest")
    parser.add_argument("--fake-changed", action="store_true", help="Finge hash alterado")
    args = parser.parse_args()

    if SMOKE_DISABLE.is_file():
        print("smoke.disable presente (pulando smoke)")
        sys.exit(0)

    if args.check_log:
        ok, why = check_log(Path(args.check_log), 0)
        print(f"log: {'OK' if ok else 'FALHA'} ({why}) [0.00s]")
        sys.exit(0 if ok else 1)

    env = load_env()
    token = env.get("PERSONAL_LINK_TOKEN", "")
    public_base = env.get("PUBLIC_BASE_URL", "").rstrip("/")
    ntfy_topic = env.get("NTFY_TOPIC", "").strip()

    if not token:
        print("ERRO: PERSONAL_LINK_TOKEN não encontrado no .env")
        sys.exit(1)

    current_hash = compute_code_hash(fake_changed=args.fake_changed)
    log_path = Path(args.log_file)

    with httpx.Client(base_url=LOCAL_BASE_URL, timeout=45.0) as client:
        results, all_ok, _ = run_all_checks(
            client=client,
            token=token,
            public_base=public_base,
            log_path=log_path,
            log_offset=args.log_offset,
            force_fail=args.force_fail
        )

    if all_ok:
        print("SMOKE OK")
        save_smoke_last(results, True)
        last_good_hash = LAST_GOOD_SHA1.read_text(encoding="utf-8").strip() if LAST_GOOD_SHA1.is_file() else ""
        if current_hash != last_good_hash or not LAST_GOOD_TAR.is_file():
            create_snapshot(current_hash)
        sys.exit(0)
    else:
        failed = [r["name"] for r in results if not r["ok"]]
        print(f"SMOKE FALHOU: {', '.join(failed)}")
        save_smoke_last(results, False)

        last_good_hash = LAST_GOOD_SHA1.read_text(encoding="utf-8").strip() if LAST_GOOD_SHA1.is_file() else ""
        has_snapshot = LAST_GOOD_TAR.is_file()

        # Só restaura quando a falha indica código quebrado. Falhas de rede/fonte
        # (poucos streams, link de vídeo fora) não desfazem uma mudança legítima.
        code_broken = any(
            r["name"] in ("manifest", "catalogos", "log")
            or (
                r["name"].startswith("stream_")
                and str(r["why"]).startswith(("status 5", "erro na requisição", "resposta não é json"))
            )
            for r in results
            if not r["ok"]
        )
        if not code_broken:
            print("Falha parece externa (fonte/rede): sem restauração.")

        if has_snapshot and current_hash != last_good_hash and code_broken:
            print("Restaurando para a última versão boa...")
            if not restore_snapshot():
                print("ERRO: falha ao extrair snapshot.")
                send_notification(ntfy_topic, failed, False)
                sys.exit(1)

            if not restart_comet(token):
                print("ERRO: Comet não respondeu após restauração.")
                send_notification(ntfy_topic, failed, False)
                sys.exit(1)

            print("\n--- Executando 2º smoke após restauração ---")
            os.environ.pop("SMOKE_FORCE_FAIL", None)
            os.environ.pop("SMOKE_FAKE_CHANGED", None)

            new_offset = 0
            if log_path.is_file():
                try:
                    new_offset = log_path.stat().st_size
                except Exception:
                    new_offset = 0

            with httpx.Client(base_url=LOCAL_BASE_URL, timeout=45.0) as client2:
                rerun_results, rerun_ok, _ = run_all_checks(
                    client=client2,
                    token=token,
                    public_base=public_base,
                    log_path=log_path,
                    log_offset=new_offset,
                    force_fail=False
                )

            save_smoke_last(rerun_results, rerun_ok)

            if rerun_ok:
                print("SMOKE OK")
                print("RESTAURADO")
                send_notification(ntfy_topic, failed, True)
                sys.exit(0)
            else:
                rerun_failed = [r["name"] for r in rerun_results if not r["ok"]]
                print(f"SMOKE FALHOU: {', '.join(rerun_failed)}")
                send_notification(ntfy_topic, rerun_failed, True)
                sys.exit(1)
        else:
            send_notification(ntfy_topic, failed, False)
            sys.exit(1)


if __name__ == "__main__":
    main()
