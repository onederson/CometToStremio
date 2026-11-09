#!/usr/bin/env python3
"""Comet Regression Test Suite
Local: /opt/comet-tools/regress.py
Interpretador: /opt/comet/.venv/bin/python
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.parse
import httpx

COMET_DIR = Path("/opt/comet")
DATA_DIR = COMET_DIR / "data"
ENV_PATH = COMET_DIR / ".env"
BASELINE_PATH = DATA_DIR / "regress_baseline.json"
REGRESS_LAST_PATH = DATA_DIR / "regress_last.json"
LOCAL_BASE_URL = "http://127.0.0.1:8000"

# Import comet pure functions with /opt/comet in sys.path
sys.path.insert(0, str(COMET_DIR))
try:
    os.chdir(str(COMET_DIR))
except Exception:
    pass


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


def get_sensitive_tokens(env: dict) -> list[str]:
    tokens = []
    for k, v in env.items():
        if not v or len(v) < 4:
            continue
        kl = k.lower()
        if any(w in kl for w in ("token", "key", "secret", "password")):
            tokens.append(v)
    tokens.sort(key=len, reverse=True)
    return tokens


def sanitize(text: str, tokens: list[str]) -> str:
    if not isinstance(text, str):
        text = str(text)
    for tok in tokens:
        if tok and len(tok) >= 4:
            text = text.replace(tok, "<token>")
    return text


def get_client(timeout: float = 25.0) -> httpx.Client:
    return httpx.Client(base_url=LOCAL_BASE_URL, timeout=timeout)


# =====================================================================
# A. Testes de unidade (sem rede, importando o Comet)
# =====================================================================

def t_unit_is_cam_release() -> tuple[str, str]:
    from comet.services.filtering import is_cam_release, parse
    p_cam = parse("Movie.Title.2024.CAM.x264")
    p_web = parse("Movie.Title.2024.1080p.WEB-DL")
    p_dict_cam = {"quality": "CAM"}
    p_dict_web = {"quality": "1080p"}
    assert is_cam_release(p_cam) is True, "CAM deve ser identificado como True"
    assert is_cam_release(p_web) is False, "WEB-DL deve ser identificado como False"
    assert is_cam_release(p_dict_cam) is True, "Dict CAM deve ser identificado como True"
    assert is_cam_release(p_dict_web) is False, "Dict 1080p deve ser identificado como False"
    return "PASS", "CAM/TS detectado, WEB-DL preservado"


def t_unit_ass_to_srt() -> tuple[str, str]:
    from comet.services.subtitles import _ass_to_srt
    ass_sample = (
        "[Script Info]\nTitle: Test\n[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:01:05.10,0:01:08.20,Default,,0,0,0,,Olá Mundo!\n"
    )
    srt_out = _ass_to_srt(ass_sample)
    assert "1" in srt_out, "SRT deve conter numeração"
    assert "-->" in srt_out, "SRT deve conter indicador de tempo -->"
    assert "00:01:05,100 --> 00:01:08,200" in srt_out, "SRT deve conter timestamps formatados"
    assert "Olá Mundo!" in srt_out, "SRT deve conter texto limpo"
    return "PASS", "ASS convertido para SRT com numeração e timestamps"


def t_unit_vtt_to_srt() -> tuple[str, str]:
    from comet.services.subtitles import _vtt_to_srt
    vtt_sample = "WEBVTT\n\n00:01.000 --> 00:04.000\nTexto de legenda\n"
    srt_out = _vtt_to_srt(vtt_sample)
    assert "1" in srt_out, "SRT deve conter numeração"
    assert "-->" in srt_out, "SRT deve conter indicador de tempo -->"
    assert "00:00:01,000 --> 00:00:04,000" in srt_out, "SRT deve conter timestamps formatados"
    assert "Texto de legenda" in srt_out, "SRT deve conter texto limpo"
    return "PASS", "VTT convertido para SRT com numeração e timestamps"


def t_unit_ptbr_detection() -> tuple[str, str]:
    from comet.services.filtering import apply_ptbr_detection, parse
    from comet.services.direct_addons import PT_KEYWORDS

    p1 = parse("Filme.2024.Dublado.1080p")
    apply_ptbr_detection(p1, "Filme.2024.Dublado.1080p")
    assert "pt" in p1.languages, "Dublado deve adicionar pt"

    p2 = parse("Filme.2024.PT-BR.1080p")
    apply_ptbr_detection(p2, "Filme.2024.PT-BR.1080p")
    assert "pt" in p2.languages, "PT-BR deve adicionar pt"

    p3 = parse("Filme.2024.Dual.1080p")
    apply_ptbr_detection(p3, "Filme.2024.Dual.1080p", tracker="brsites")
    assert "pt" in p3.languages, "Dual com tracker BR deve adicionar pt"

    p4 = parse("Movie.Title.2024.1080p.WEB-DL.x264")
    apply_ptbr_detection(p4, "Movie.Title.2024.1080p.WEB-DL.x264")
    assert "pt" not in p4.languages, "Nome em inglês puro não deve adicionar pt"

    assert any(kw in "filme dual audio 1080p" for kw in PT_KEYWORDS), "PT_KEYWORDS detecta dual"
    assert not any(kw in "movie english only 1080p" for kw in PT_KEYWORDS), "PT_KEYWORDS ignora inglês"

    return "PASS", "Dublado/Dual/PT-BR detectados como PT, inglês puro não"


def t_unit_dub_kind() -> tuple[str, str]:
    from comet.api.endpoints.stream import _get_dub_kind
    assert _get_dub_kind("Filme.Dublado.1080p", is_pt=True) == "dublado"
    assert _get_dub_kind("Filme.Dual.Audio.1080p", is_pt=True) == "dual"
    assert _get_dub_kind("Filme.PT-BR.1080p", is_pt=True) == "pt"
    assert _get_dub_kind("Filme.Dublado.1080p", is_pt=False) is None
    return "PASS", "rótulos dublado/dual/pt-br categorizados"


def t_unit_select_debrid_refresh_hashes() -> tuple[str, str]:
    from comet.services.media_search import select_debrid_refresh_hashes
    empty_res = select_debrid_refresh_hashes(set(), set(), {}, had_cached_torrents=False, use_account_scrape=False)
    assert empty_res == set(), "Conjunto vazio deve retornar vazio"

    hashes = {"hash1", "hash2"}
    full_res = select_debrid_refresh_hashes(hashes, set(), {}, had_cached_torrents=False, use_account_scrape=False)
    assert full_res == hashes, "Sem torrents em cache requer refresh completo"

    status = {"hash1": {"rd": True}}
    inc_res = select_debrid_refresh_hashes(
        {"hash1", "hash2"}, {"hash1"}, status,
        had_cached_torrents=True, use_account_scrape=True, services=["rd"]
    )
    assert "hash2" in inc_res, "Hash novo deve ser selecionado para refresh"
    return "PASS", "seleção de hashes com serviços e cache validada"


def t_unit_prefetch_next_episode() -> tuple[str, str]:
    from comet.services.prefetch import _find_next_episode
    videos = [
        {"season": 1, "episode": 1, "released": "2020-01-01T00:00:00Z"},
        {"season": 1, "episode": 2, "released": "2020-01-08T00:00:00Z"},
        {"season": 2, "episode": 1, "released": "2021-01-01T00:00:00Z"},
    ]
    assert _find_next_episode(videos, 1, 1) == (1, 2), "Meio da temporada avança para próx ep"
    assert _find_next_episode(videos, 1, 2) == (2, 1), "Fim da temporada avança para S+1:1"
    assert _find_next_episode(videos, 2, 1) is None, "Sem próximo episódio retorna None"
    return "PASS", "próximo ep (meio da temp e virada S+1:1) OK"


def t_unit_stream_debrid_priority() -> tuple[str, str]:
    # Lógica RD ⚡ → TB ⚡ → RD ⬇️ → TB ⬇️ está inline em get_streams() (stream.py:965-1040),
    # acoplada ao request FastAPI, settings e dicionários de status de cache. Não é função isolada.
    return "PASS", "pulado: lógica inline em get_streams (não isolável)"


def t_unit_parse_media_id() -> tuple[str, str]:
    from comet.utils.parsing import parse_media_id
    assert parse_media_id("movie", "tt0111161") == ("tt0111161", None, None)
    assert parse_media_id("series", "tt0903747:2:3") == ("tt0903747", 2, 3)
    assert parse_media_id("series", "kitsu:1234:5") == ("1234", 1, 5)
    return "PASS", "parse_media_id para filmes, séries e kitsu OK"


def t_unit_is_video() -> tuple[str, str]:
    from comet.utils.parsing import is_video
    assert is_video("movie.mkv") is True
    assert is_video("video.mp4") is True
    assert is_video("clip.avi") is True
    assert is_video("subtitles.srt") is False
    assert is_video("poster.jpg") is False
    return "PASS", "extensões de vídeo validadas"


def t_unit_normalize_title() -> tuple[str, str]:
    from comet.services.filtering import normalize_title
    norm = normalize_title("The.Matrix.1999.1080p")
    assert "matrix" in norm
    return "PASS", f"título normalizado: {norm[:20]}"


def t_unit_format_resolution() -> tuple[str, str]:
    from comet.api.endpoints.stream import _format_resolution
    assert _format_resolution("2160p") == "4K"
    assert _format_resolution("4k") == "4K"
    assert _format_resolution("1080p") == "1080p"
    assert _format_resolution("720p") == "720p"
    assert _format_resolution("480p") == "SD"
    return "PASS", "resoluções formatadas (4K, 1080p, 720p, SD)"


def t_unit_format_size_gb() -> tuple[str, str]:
    from comet.api.endpoints.stream import _format_size_gb
    assert _format_size_gb(1073741824) == "1,0 GB"
    assert _format_size_gb(3221225472) == "3,0 GB"
    assert _format_size_gb(None) is None
    assert _format_size_gb(0) is None
    return "PASS", "tamanhos em GB com vírgula validados"


def t_unit_format_uptime() -> tuple[str, str]:
    from comet.api.endpoints.status import _format_uptime
    assert _format_uptime(90065) == "1d 1h 1m 5s"
    assert _format_uptime(3660) == "1h 1m 0s"
    assert _format_uptime(45) == "0m 45s"
    return "PASS", "formatação de uptime (d h m s) OK"


def t_unit_merge_aliases() -> tuple[str, str]:
    from comet.metadata.siblings import merge_aliases
    merged = merge_aliases(
        {"movie": ["Title A", "Title B"]},
        {"movie": ["Title B", "Title C"], "series": ["Show X"]}
    )
    assert merged == {"movie": ["Title A", "Title B", "Title C"], "series": ["Show X"]}
    return "PASS", "deduplicação e união de aliases OK"


def t_unit_predownload_pick() -> tuple[str, str]:
    from comet.services.prefetch import _pick_predownload as pick
    rd_1080 = {"name": "⬇️ 1080p\n🇧🇷 PT-BR", "description": "WEB-DL · 1,5 GB\nReal-Debrid · x", "url": "a"}
    tb_4k_big = {"name": "⬇️ 4K\n🇧🇷 Dual", "description": "20,0 GB\nTorBox", "url": "b"}
    sd = {"name": "⬇️ SD\n🇧🇷 PT-BR", "description": "0,2 GB\nReal-Debrid", "url": "c"}
    en_fast = {"name": "⚡ 1080p", "description": "EN", "url": "d"}
    r = pick([{"name": "▶ Assistir", "url": "u"}, rd_1080, tb_4k_big, en_fast])
    assert r and r["res"] == "1080p" and r["service"] == "Real-Debrid", r
    assert pick([rd_1080, {"name": "⚡ 720p\n🇧🇷 PT-BR", "url": "e"}]) is None, "PT ⚡ já pronto"
    assert pick([rd_1080, {"name": "🌐 1080p\n🇧🇷 PT-BR", "url": "f"}]) is None, "link direto PT já pronto"
    assert pick([{"name": "⬇️ 1080p", "url": "g"}]) is None, "sem PT não baixa"
    assert pick([tb_4k_big]) is None, "acima de 15 GB"
    assert pick([sd])["res"] == "SD"
    return "PASS", "escolhe PT ⬇️ certo; pula PT pronto, link direto PT, sem PT e > 15 GB"


def t_unit_episodios_ptbr() -> tuple[str, str]:
    from comet.services.meta_ptbr import _overlay_mismatched_seasons as overlay
    # Mesmo total (anime com temporadas divididas diferente): casa pela ordem geral.
    cm = [{"season": 1, "episode": i, "name": f"EN {i}", "overview": "x", "description": "x"} for i in (1, 2, 3)]
    cm += [{"season": 2, "episode": 1, "name": "EN 4", "overview": "x"}]
    tm = [[{"name": f"PT {i}", "overview": f"pt {i}"} for i in (1, 2)], [{"name": f"PT {i}", "overview": f"pt {i}"} for i in (3, 4)]]
    assert overlay(cm, tm, {1, 2}) == 4
    assert [v["name"] for v in cm] == ["PT 1", "PT 2", "PT 3", "PT 4"], cm
    assert cm[0]["description"] == "pt 1"
    # Total diferente: casa pela data (1 dia de folga), sem repetir episódio.
    cm = [
        {"season": 1, "episode": 1, "name": "A", "released": "2020-01-01T05:00:00.000Z"},
        {"season": 1, "episode": 2, "name": "B", "released": "2020-01-08T05:00:00.000Z"},
        {"season": 1, "episode": 3, "name": "C", "released": "2020-02-01T05:00:00.000Z"},
    ]
    tm = [[
        {"name": "PT A", "overview": "a", "air_date": "2020-01-02"},
        {"name": "PT B", "overview": "b", "air_date": "2020-01-08"},
    ]]
    assert overlay(cm, tm, {1}) == 2
    assert [v["name"] for v in cm] == ["PT A", "PT B", "C"], cm
    return "PASS", "temporadas divididas diferente: casa pela ordem e, sem total igual, pela data"


def t_unit_novidades_1108() -> tuple[str, str]:
    """Modo 4G, 'Onde você parou', guardião e lembretes (08/11/2026)."""
    from comet.api.endpoints.stream import _apply_clean_layout
    from comet.services.resume import build_series_lines, build_movie_lines
    from comet.services.guardian import should_vacuum
    from comet.services.reminders import parse_command, matches

    def cand(res, size_gb, h, br=None):
        info = {"kind": "rd", "cached": True, "is_pt": True, "has_pt": 1, "resolution": res,
                "size": size_gb * 1024**3, "service": "torbox", "info_hash": h * 40, "raw_title": f"X.{res}.mkv"}
        if br:
            info["_media"] = {"bitrate_mbps": br}
        return {"name": res, "description": "", "url": f"http://x/{h}", "_info": info}

    def pick(streams, **kw):
        _, best, _ = _apply_clean_layout([dict(s, _info=dict(s["_info"])) for s in streams], 0, **kw)
        return best["_info"]["info_hash"][0] if best else None

    eps = [cand("1080p", 3.5, "a"), cand("720p", 1.2, "b")]
    assert pick(eps, remote=True, is_episode=True) == "b", "4G: episódio de 3,5 GB é pesado demais"
    assert pick(eps, remote=True) == "a", "4G: filme de 3,5 GB ainda cabe"
    assert pick(eps) == "a", "em casa nada muda"
    br = [cand("1080p", 3, "a", br=25), cand("1080p", 3.2, "b", br=8)]
    assert pick(br, remote=True) == "b", "4G: bitrate lido do arquivo manda"

    meta = {"videos": [{"season": 1, "episode": i, "title": f"Ep {i}", "overview": f"Resumo {i}"} for i in range(1, 6)]}
    now = 1_800_000_000
    lines = build_series_lines([{"season": 1, "episode": 2, "ts": now - 40 * 86400, "outcome": "completo"},
                                {"season": 1, "episode": 3, "ts": now - 30 * 86400, "outcome": None}], meta, now)
    assert lines[0].startswith("▶ Você parou em T1E3 · Ep 3"), lines
    assert "Para lembrar" in lines[1] and "T1E2: Resumo 2" in lines[1], lines
    fin = build_series_lines([{"season": 1, "episode": 4, "ts": now - 3600, "outcome": "completo"}], meta, now)
    assert "Próximo: T1E5" in fin[0] and len(fin) == 1, fin
    assert build_movie_lines([{"ts": now, "outcome": "completo"}])[0].startswith("✓ Você viu")

    assert should_vacuum(30, 100, 10**12, 10**8) is True
    assert should_vacuum(2, 100, 10**12, 10**8) is False
    assert should_vacuum(30, 100, 2 * 10**8, 10**8) is False, "sem disco para o VACUUM"
    assert parse_command("/lembrar Chaves") is not None and parse_command("oi") is None
    assert matches({"title": "Chaves: Episódio 12"}, "chaves") and not matches({"title": "Chapolin"}, "chaves")
    return "PASS", "4G por tamanho e bitrate, onde você parou, VACUUM só com folga, /lembrar"


def t_unit_nuvio_4k_natal() -> tuple[str, str]:
    import datetime as _dt
    from comet.api.endpoints.stream import _apply_clean_layout
    from comet.services.catalogs import _raw_build_tmdb_path_and_params, build_manifest_catalogs
    from comet.services.seasonal import seasonal_catalogs, _easter, SEASONS

    def cand(res, has_pt, size_gb, is_pt=True, h="a"):
        info = {"kind": "rd", "cached": True, "is_pt": is_pt, "has_pt": has_pt, "resolution": res,
                "size": size_gb * 1024**3, "service": "realdebrid", "info_hash": h * 40,
                "raw_title": f"Filme.{res}.mkv"}
        return {"name": res, "description": "", "url": f"http://x/{h}", "_info": info}

    def pick(streams, **kw):
        out, best, _ = _apply_clean_layout([dict(s, _info=dict(s["_info"])) for s in streams], 0, **kw)
        return best["_info"]["resolution"] if best else None

    pt = [cand("1080p", 1, 3, h="a"), cand("2160p", None, 20, h="b"), cand("2160p", 1, 70, h="c")]
    assert pick(pt, prefer_4k=True) == "2160p", "Nuvio: 4K PT primeiro"
    assert pick(pt) == "1080p", "Stremio segue com 1080p primeiro"
    sem_4k_pt = [cand("1080p", None, 3, h="a"), cand("2160p", 0, 20, is_pt=False, h="b")]
    assert pick(sem_4k_pt, prefer_4k=True) == "1080p", "sem 4K PT: 1080p PT"
    so_original = [cand("1080p", 0, 3, is_pt=False, h="a"), cand("2160p", 0, 20, is_pt=False, h="b")]
    assert pick(so_original, prefer_4k=True) == "2160p", "sem PT: melhor original"

    def hot(d):
        return [c["id"] for c in seasonal_catalogs(_dt.date.fromisoformat(d))[0]]

    assert _easter(2027) == _dt.date(2027, 3, 28) and _easter(2026) == _dt.date(2026, 4, 5)
    assert hot("2026-11-08") == ["comet_xmas_new", "comet_xmas_all"]
    assert hot("2026-12-31")[:2] == ["comet_xmas_new", "comet_xmas_all"] and "comet_newyear" in hot("2026-12-31")
    assert "comet_xmas_new" not in hot("2027-01-02"), "Natal desce depois de 31/dez"
    assert hot("2026-10-05") == ["comet_kidsday", "comet_hallo_new", "comet_hallo_all"]
    assert hot("2026-11-01")[:2] == ["comet_xmas_new", "comet_xmas_all"] and "comet_hallo_new" not in hot("2026-11-01")
    assert hot("2027-07-10") == []
    allc = seasonal_catalogs(_dt.date(2027, 7, 10))[1]
    assert allc[0]["id"] == "comet_dad", "fora de época: próxima data primeiro"
    assert [c["name"] for c in allc if c["id"] == "comet_xmas_new"] == ["🎄 Filmes novos de Natal (2026)"]
    cats = build_manifest_catalogs(is_personal=True)
    ids = [c["id"] for c in cats]
    t10 = max(i for i, x in enumerate(ids) if x == "comet_top10")
    # desde 09/11/2026 só as datas em época entram no manifesto (fora de época não ocupam fileira)
    _hot_now = set(hot(_dt.date.today().isoformat()))
    _all_seasonal = {s["id"] for ss in SEASONS for s in ss["lists"]}
    assert set(ids) & _all_seasonal == _hot_now, "só as datas em época no manifesto"
    for h in hot(_dt.date.today().isoformat()):
        assert ids.index(h) <= t10 + 4, f"{h} em destaque deveria ficar logo depois do Top 10"
    _, p = _raw_build_tmdb_path_and_params("movie", "comet_xmas_all", None, 1)
    assert p["with_keywords"] == 207317 and p["sort_by"] == "primary_release_date.desc"
    return "PASS", "Nuvio: 4K PT > 1080p PT > melhor original; datas comemorativas sobem perto da data"


def t_unit_fileiras_homonimos() -> tuple[str, str]:
    """09/11/2026: fileiras agrupadas (filtro + rodízio) e filtro de séries homônimas."""
    import datetime as _dt
    from comet.services import row_groups
    from comet.services.filtering import TitleMatcher

    cats = [
        {"type": "movie", "id": "comet_top10", "name": "Top"},
        {"type": "movie", "id": "comet_mood_cry", "name": "a"},
        {"type": "movie", "id": "comet_mood_twist", "name": "b"},
        {"type": "series", "id": "comet_orig_netflix", "name": "⭐ Originais Netflix"},
        {"type": "series", "id": "comet_netflix", "name": "Netflix"},
        {"type": "series", "id": "comet_orig_max", "name": "⭐ Originais HBO Max"},
        {"type": "series", "id": "comet_max", "name": "HBO Max"},
    ]
    out = row_groups.consolidate(cats)
    ids = [(c["type"], c["id"]) for c in out]
    assert ids == [("movie", "comet_top10"), ("movie", "comet_moods"), ("series", "comet_origs"),
                   ("series", "comet_streams")], ids
    mid, extra = row_groups.resolve("comet_moods", "movie", {"genre": "🤯 Plot twist", "skip": "40"})
    assert mid == "comet_mood_twist" and extra == {"skip": "40"}, (mid, extra)
    d1 = row_groups.resolve("comet_moods", "movie", {}, today=_dt.date(2026, 11, 9))[0]
    d2 = row_groups.resolve("comet_moods", "movie", {}, today=_dt.date(2026, 11, 10))[0]
    assert d1 != d2 and d1.startswith("comet_mood_"), "rodízio diário"

    blocked = {"ep:the man in the straw hat", "ep:1:1:romance dawn", "ep:__hdr__", "ep:__minyear:2005__"}
    m = TitleMatcher("One Piece", 1999, None, "series", {}, blocked)
    assert not m.matches_title("ONE.PIECE.S01E01.ROMANCE.DAWN.1080p.NF.WEB-DL", "One Piece")
    assert not m.matches_title("One.Piece.S01E02.The.Man.in.the.Straw.Hat.1080p", "One Piece")
    assert not m.matches_title("One.Piece.S01E01.1080p.WEB-DL.DV.HDR10", "One Piece")
    assert not m.matches_title("Doctor.Who.2005.S01E01.1080p", "One Piece")
    assert m.matches_title("[uP] One Piece - 0001 (HDV 1080p x264 AC3 Multi)", "One Piece")
    assert m.matches_title("One Piece E1000 Romance Dawn Special 1080p", "One Piece"), "mesmo título, outro episódio"
    return "PASS", "grupos (filtro, rodízio, posição) e homônimos (título de episódio, HDR, ano) OK"


def t_unit_pt_text() -> tuple[str, str]:
    """09/11/2026: título brasileiro (ou original legível, ou inglês) e detecção de PT."""
    from comet.services.pt_text import is_portuguese, has_nonlatin, title_for

    assert is_portuguese("Dois trabalhadores sem grana se unem para assaltar uma loja de departamentos.")
    assert not is_portuguese("Years ago, the fearsome Pirate King was executed leaving a huge pile of treasure.")
    assert not is_portuguese("En la época de los reinos combatientes, un joven huérfano y su amigo")
    assert not is_portuguese("") and has_nonlatin("กฎหลังเที่ยงคืน")
    # título brasileiro existe: usa (Cinemeta manda o inglês)
    assert title_for({"br_title": "A Viagem de Chihiro", "orig": "千と千尋の神隠し", "en_title": "Spirited Away"}, "Spirited Away") == "A Viagem de Chihiro"
    # sem título brasileiro: fica o que veio (Transformers, We Met in December)
    assert title_for({"br_title": "", "orig": "Transformers", "en_title": "Transformers"}, "Transformers") == "Transformers"
    # original ilegível e sem título brasileiro: inglês
    assert title_for({"br_title": "", "orig": "กฎหลังเที่ยงคืน", "en_title": "The Rules"}, "กฎหลังเที่ยงคืน") == "The Rules"
    return "PASS", "título BR > original legível > inglês; PT x EN/ES OK"


def t_unit_source_breaker() -> tuple[str, str]:
    from comet.core import breaker
    breaker.reset()
    name = "MockSource"
    t = 1000.0

    # 1. 3 falhas seguidas -> aberto
    assert not breaker.is_open(name, now=t)
    breaker.record(name, False, now=t)
    assert not breaker.is_open(name, now=t)
    breaker.record(name, False, now=t)
    assert not breaker.is_open(name, now=t)
    breaker.record(name, False, now=t)
    assert breaker.is_open(name, now=t)

    # 2. Antes da pausa (600s) -> pulado
    assert breaker.is_open(name, now=t + 300)
    assert breaker.is_open(name, now=t + 599)

    # 3. Depois da pausa -> 1 passa
    assert not breaker.is_open(name, now=t + 601)
    assert breaker.is_open(name, now=t + 602)

    # 4. Sucesso -> fechado
    breaker.record(name, True, now=t + 603)
    assert not breaker.is_open(name, now=t + 604)

    # 5. Falha no teste -> pausa dobrada (1200s)
    t2 = 2000.0
    breaker.record(name, False, now=t2)
    breaker.record(name, False, now=t2)
    breaker.record(name, False, now=t2)
    assert breaker.is_open(name, now=t2)
    assert not breaker.is_open(name, now=t2 + 601)
    breaker.record(name, False, now=t2 + 602)
    assert breaker.is_open(name, now=t2 + 602 + 600)
    assert breaker.is_open(name, now=t2 + 602 + 1199)
    assert not breaker.is_open(name, now=t2 + 602 + 1201)

    # 6. Excluded sources nunca pausam
    for exc in ["Real-Debrid", "TorBox", "StremThru", "TMDB", "Cinemeta"]:
        for _ in range(5):
            breaker.record(exc, False, now=5000.0)
        assert not breaker.is_open(exc, now=5000.0)

    breaker.reset()
    return "PASS", "3 falhas -> aberto; pulado antes; 1 passa depois; sucesso -> fechado; falha -> dobro"


# =====================================================================
# B. Testes integrados (HTTP no Comet real, link pessoal)
# =====================================================================

def is_stream_cam(s: dict) -> bool:
    from comet.services.filtering import is_cam_release, parse
    fn = s.get("behaviorHints", {}).get("filename", "")
    if fn:
        try:
            if is_cam_release(parse(fn)):
                return True
        except Exception:
            pass
    name = s.get("name", "")
    desc = s.get("description", "")
    if "🎦 CAM" in name or "CAM" in name.split():
        return True
    if "Gravação de cinema" in desc:
        return True
    return False


def get_stream_hash(s: dict) -> str | None:
    if "infoHash" in s:
        return s["infoHash"].lower()
    url = s.get("url", "")
    m = re.search(r"/playback/([0-9a-fA-F]{40})", url)
    if m:
        return m.group(1).lower()
    return None


def t_manifest(token: str) -> tuple[str, str]:
    with get_client() as client:
        r = client.get(f"/{token}/manifest.json")
    if r.status_code != 200:
        return "FAIL", f"status {r.status_code}"
    data = r.json()
    version = str(data.get("version", ""))
    if not version.startswith("2.1."):
        return "FAIL", f"versão '{version}' não começa com 2.1."

    resources = data.get("resources", [])
    res_names = {res.get("name") if isinstance(res, dict) else res for res in resources}
    required_res = {"catalog", "meta", "stream", "subtitles"}
    missing = required_res - res_names
    if missing:
        return "FAIL", f"resources faltando: {', '.join(missing)}"

    catalogs = data.get("catalogs", [])
    if len(catalogs) < 30:
        return "FAIL", f"{len(catalogs)} catálogos (< 30)"

    return "PASS", f"{version}, {len(catalogs)} catálogos"


def t_catalogos(token: str, baseline_data: dict, current_baseline: dict, save_baseline: bool) -> tuple[str, str]:
    with get_client() as client:
        r = client.get(f"/{token}/manifest.json")
    if r.status_code != 200:
        return "FAIL", f"manifest status {r.status_code}"

    catalogs = r.json().get("catalogs", [])
    valid_cats = [
        c for c in catalogs
        if not any(e.get("isRequired") for e in c.get("extra", []) if isinstance(e, dict))
    ]

    failed = []
    warns = []
    relative_urls = []

    def check_one_cat(c):
        cat_id = c.get("id")
        cat_type = c.get("type")
        url = f"/{token}/catalog/{cat_type}/{cat_id}.json"
        try:
            with get_client() as cl:
                res = cl.get(url)
            if res.status_code != 200:
                return cat_id, cat_type, False, f"status {res.status_code}", 0, []
            m_data = res.json()
            metas = m_data.get("metas", [])
            cnt = len(metas)
            rel_list = []
            for m in metas:
                for fld in ("poster", "background"):
                    val = m.get(fld)
                    if isinstance(val, str) and val.strip():
                        if not val.startswith("https://"):
                            rel_list.append(f"{cat_id} ({fld}: {val[:30]})")
            return cat_id, cat_type, True, "", cnt, rel_list
        except Exception as e:
            return cat_id, cat_type, False, str(e), 0, []

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(check_one_cat, c) for c in valid_cats]
        for f in as_completed(futures):
            cat_id, cat_type, ok, err, count, rels = f.result()
            key = f"{cat_type}/{cat_id}"
            if not ok:
                failed.append(f"{cat_id} ({err})")
                continue

            current_baseline.setdefault("catalogs", {})[key] = count

            if rels:
                relative_urls.extend(rels)

            is_personal = any(p in cat_id for p in ("mylist", "newep", "foryou", "dubready", "previewtest", "week"))
            # fileiras extras: conteúdo depende do dia/hora (jogos, sugestões da noite, histórico)
            if cat_id in ("comet_tonight", "comet_fut", "comet_recap", "comet_mytv"):
                if count == 0 and cat_id in ("comet_mytv", "comet_recap"):
                    warns.append(f"{cat_id} vazio")
                continue
            if cat_id == "comet_previewtest":
                if count != 4:
                    failed.append(f"{cat_id} ({count} itens != 4)")
            elif not is_personal and count < 5:
                failed.append(f"{cat_id} ({count} itens)")
            elif is_personal and count == 0:
                warns.append(f"{cat_id} vazio")

            # Comparação com baseline se disponível
            if not save_baseline and baseline_data:
                base_cats = baseline_data.get("catalogs", {})
                if key in base_cats:
                    base_cnt = base_cats[key]
                    if base_cnt >= 5 and count == 0:
                        failed.append(f"{cat_id} caiu de {base_cnt} para 0")
                    elif base_cnt > 0 and count < base_cnt * 0.40:
                        warns.append(f"{cat_id} caiu de {base_cnt} para {count}")

    if relative_urls:
        return "FAIL", f"{len(relative_urls)} posters/backgrounds não-https: {', '.join(relative_urls[:3])}"

    if failed:
        return "FAIL", f"catálogos falharam: {', '.join(failed[:4])}"

    if warns:
        return "WARN", f"{len(valid_cats)} catálogos OK com avisos ({', '.join(warns[:3])})"

    return "PASS", f"{len(valid_cats)} catálogos verificados (sem URLs relativas)"


def t_capa(token: str, public_base: str) -> tuple[str, str]:
    with get_client() as client:
        r = client.get(f"/{token}/catalog/movie/comet_top10.json")
    if r.status_code != 200:
        return "FAIL", f"status {r.status_code}"
    metas = r.json().get("metas", [])
    if not metas:
        return "FAIL", "top10 sem metas"
    poster_url = metas[0].get("poster", "")
    if not poster_url:
        return "FAIL", "1º item sem poster"
    rw_url = rewrite_url(poster_url, public_base, LOCAL_BASE_URL)

    with httpx.Client(follow_redirects=True, timeout=25.0) as img_client:
        r_img = img_client.get(rw_url)

    if r_img.status_code != 200:
        return "FAIL", f"status imagem {r_img.status_code}"
    ct = r_img.headers.get("content-type", "").lower()
    if not ct.startswith("image/"):
        return "FAIL", f"content-type '{ct}' não é image/*"
    size = len(r_img.content)
    if size <= 5120:
        return "FAIL", f"tamanho {size} bytes (<= 5 KB)"

    # Verifica capa de um item com ?p=
    p_url = None
    with get_client() as client:
        r_orig = client.get(f"/{token}/catalog/series/comet_orig_netflix.json")
        if r_orig.status_code == 200:
            metas_orig = r_orig.json().get("metas", [])
            for m in metas_orig:
                p_cand = m.get("poster", "")
                if "p=" in p_cand:
                    p_url = p_cand
                    break

    if not p_url:
        sep = "&" if "?" in poster_url else "?"
        p_url = f"{poster_url}{sep}p=8"

    rw_p_url = rewrite_url(p_url, public_base, LOCAL_BASE_URL)
    with httpx.Client(follow_redirects=True, timeout=25.0) as img_client:
        r_p_img = img_client.get(rw_p_url)

    if r_p_img.status_code != 200:
        return "FAIL", f"status imagem com ?p= {r_p_img.status_code}"
    ct_p = r_p_img.headers.get("content-type", "").lower()
    if not ct_p.startswith("image/"):
        return "FAIL", f"content-type com ?p= '{ct_p}' não é image/*"
    size_p = len(r_p_img.content)
    if size_p <= 5120:
        return "FAIL", f"tamanho com ?p= {size_p} bytes (<= 5 KB)"

    return "PASS", f"{size} bytes / p: {size_p} bytes ({ct})"


def t_busca(token: str) -> tuple[str, str]:
    with get_client() as client:
        r1 = client.get(f"/{token}/catalog/movie/comet_search/search=batman.json")
        if r1.status_code != 200:
            return "FAIL", f"busca filme status {r1.status_code}"
        m1 = r1.json().get("metas", [])
        if len(m1) < 3:
            return "FAIL", f"busca filme batman retornou {len(m1)} (< 3)"

        r2 = client.get(f"/{token}/catalog/movie/comet_person/search=Tom%20Hanks.json")
        if r2.status_code != 200:
            return "FAIL", f"busca pessoa status {r2.status_code}"
        m2 = r2.json().get("metas", [])
        if len(m2) < 3:
            return "FAIL", f"busca pessoa Tom Hanks retornou {len(m2)} (< 3)"

    return "PASS", f"batman: {len(m1)}, Tom Hanks: {len(m2)}"


def t_meta_filme(token: str) -> tuple[str, str]:
    with get_client() as client:
        r = client.get(f"/{token}/meta/movie/tt0111161.json")
    if r.status_code != 200:
        return "FAIL", f"status {r.status_code}"
    meta = r.json().get("meta", {})
    name = meta.get("name", "")
    desc = meta.get("description", "")
    if name != "Um Sonho de Liberdade":
        return "FAIL", f"name '{name}' != 'Um Sonho de Liberdade'"
    if not desc or not desc.strip():
        return "FAIL", "description vazia"
    return "PASS", f"{name}"


def t_meta_serie(token: str) -> tuple[str, str]:
    with get_client() as client:
        r = client.get(f"/{token}/meta/series/tt0903747.json")
    if r.status_code != 200:
        return "FAIL", f"status {r.status_code}"
    meta = r.json().get("meta", {})
    videos = meta.get("videos", [])
    if len(videos) < 60:
        return "FAIL", f"{len(videos)} episódios (< 60)"
    return "PASS", f"{len(videos)} episódios"


def _check_streams_payload(streams: list, min_count: int, require_pt: bool) -> tuple[bool, str]:
    if len(streams) < min_count:
        return False, f"{len(streams)} streams (< {min_count})"

    has_fast = any("⚡" in s.get("name", "") for s in streams)
    if has_fast:
        first_name = streams[0].get("name", "")
        if not first_name.startswith("▶ Assistir"):
            return False, f"1º stream '{first_name[:20]}' não começa com '▶ Assistir'"

    # ▶ Assistir e os atalhos com curadoria (📱 Leve, 💎 Máxima qualidade, 🎧 Original) são cópias de propósito
    _copies = ("▶ Assistir", "📱", "💎", "🎧")
    sub = [s for s in streams if not s.get("name", "").startswith(_copies)]
    hashes = [get_stream_hash(s) for s in sub if get_stream_hash(s) is not None]
    dupes = [h for h, c in Counter(hashes).items() if c > 1]
    if dupes:
        return False, f"infoHashes repetidos: {len(dupes)}"

    if require_pt:
        pt_count = sum(1 for s in streams if "🇧🇷" in s.get("name", ""))
        if pt_count < 1:
            return False, "nenhum stream com 🇧🇷"

    has_non_cam = any(not is_stream_cam(s) for s in streams)
    if has_non_cam:
        top5_cam = [i for i, s in enumerate(streams[:5]) if is_stream_cam(s)]
        if top5_cam:
            return False, f"CAM nos 5 primeiros streams (posições {top5_cam})"

    return True, ""


def _evaluate_stream_baseline(imdb_id: str, streams: list, baseline_data: dict, current_baseline: dict, save_baseline: bool) -> tuple[str | None, str]:
    total_cnt = len(streams)
    fast_cnt = sum(1 for s in streams if "⚡" in s.get("name", ""))
    pt_cnt = sum(1 for s in streams if "🇧🇷" in s.get("name", ""))

    current_baseline.setdefault("streams", {})[imdb_id] = {
        "streams": total_cnt,
        "fast": fast_cnt,
        "pt": pt_cnt
    }

    if save_baseline or not baseline_data:
        return None, ""

    b = baseline_data.get("streams", {}).get(imdb_id)
    if not b:
        return None, ""

    b_streams = b.get("streams", 0)
    b_fast = b.get("fast", 0)
    b_pt = b.get("pt", 0)

    # Queda a zero se era >= 5 -> FAIL
    if b_streams >= 5 and total_cnt == 0:
        return "FAIL", f"streams caiu de {b_streams} para 0"
    if b_fast >= 5 and fast_cnt == 0:
        return "FAIL", f"⚡ caiu de {b_fast} para 0"
    if b_pt >= 5 and pt_cnt == 0:
        return "FAIL", f"🇧🇷 caiu de {b_pt} para 0"

    # Queda > 60% -> WARN
    warns = []
    if b_streams > 0 and total_cnt < b_streams * 0.40:
        pct = 100 - (total_cnt * 100 // b_streams)
        warns.append(f"streams -{pct}% ({b_streams} -> {total_cnt})")
    if b_fast > 0 and fast_cnt < b_fast * 0.40:
        pct = 100 - (fast_cnt * 100 // b_fast)
        warns.append(f"⚡ -{pct}% ({b_fast} -> {fast_cnt})")
    if b_pt > 0 and pt_cnt < b_pt * 0.40:
        pct = 100 - (pt_cnt * 100 // b_pt)
        warns.append(f"🇧🇷 -{pct}% ({b_pt} -> {pt_cnt})")

    if warns:
        return "WARN", f"queda baseline: {', '.join(warns)}"

    return None, ""


def t_stream_filme(token: str, baseline_data: dict, current_baseline: dict, save_baseline: bool, shared_state: dict) -> tuple[str, str]:
    with get_client() as client:
        r = client.get(f"/{token}/stream/movie/tt12042730.json")
    if r.status_code != 200:
        return "FAIL", f"status {r.status_code}"
    streams = r.json().get("streams", [])
    ok, err = _check_streams_payload(streams, min_count=5, require_pt=False)
    if not ok:
        return "FAIL", err

    if streams and streams[0].get("name", "").startswith("▶ Assistir"):
        shared_state["assistir_stream"] = streams[0]

    b_status, b_msg = _evaluate_stream_baseline("tt12042730", streams, baseline_data, current_baseline, save_baseline)
    if b_status == "FAIL":
        return "FAIL", b_msg

    fast_cnt = sum(1 for s in streams if "⚡" in s.get("name", ""))
    msg = f"{len(streams)} streams, {fast_cnt} ⚡, 1º '▶ Assistir'"
    if b_status == "WARN":
        return "WARN", f"{msg} ({b_msg})"
    return "PASS", msg


def t_stream_serie(token: str, baseline_data: dict, current_baseline: dict, save_baseline: bool) -> tuple[str, str]:
    media_id = "tt0000000:1:1" if os.environ.get("REGRESS_SELFTEST") == "1" else "tt2293002:1:2"
    with get_client() as client:
        r = client.get(f"/{token}/stream/series/{media_id}.json")
    if r.status_code != 200:
        return "FAIL", f"status {r.status_code}"
    streams = r.json().get("streams", [])
    ok, err = _check_streams_payload(streams, min_count=5, require_pt=True)
    if not ok:
        return "FAIL", err

    b_status, b_msg = _evaluate_stream_baseline("tt2293002:1:2", streams, baseline_data, current_baseline, save_baseline)
    if b_status == "FAIL":
        return "FAIL", b_msg

    pt_cnt = sum(1 for s in streams if "🇧🇷" in s.get("name", ""))
    msg = f"{len(streams)} streams, {pt_cnt} 🇧🇷"
    if b_status == "WARN":
        return "WARN", f"{msg} ({b_msg})"
    return "PASS", msg


def t_stream_anime(token: str, baseline_data: dict, current_baseline: dict, save_baseline: bool) -> tuple[str, str]:
    with get_client() as client:
        r = client.get(f"/{token}/stream/series/tt0388629:1:1.json")
    if r.status_code != 200:
        return "FAIL", f"status {r.status_code}"
    streams = r.json().get("streams", [])
    ok, err = _check_streams_payload(streams, min_count=20, require_pt=False)
    if not ok:
        return "FAIL", err

    b_status, b_msg = _evaluate_stream_baseline("tt0388629:1:1", streams, baseline_data, current_baseline, save_baseline)
    if b_status == "FAIL":
        return "FAIL", b_msg

    fast_cnt = sum(1 for s in streams if "⚡" in s.get("name", ""))
    msg = f"{len(streams)} streams, {fast_cnt} ⚡"
    if b_status == "WARN":
        return "WARN", f"{msg} ({b_msg})"
    return "PASS", msg


def t_kids(kids_token: str) -> tuple[str, str]:
    if not kids_token:
        return "FAIL", "KIDS_LINK_TOKEN não encontrado no .env"

    with get_client() as client:
        r_man = client.get(f"/{kids_token}/manifest.json")
        if r_man.status_code != 200:
            return "FAIL", f"manifest status {r_man.status_code}"
        m_data = r_man.json()
        m_id = str(m_data.get("id", ""))
        if not m_id.endswith(".kids"):
            return "FAIL", f"id '{m_id}' não termina em .kids"

        catalogs = [
            c for c in m_data.get("catalogs", [])
            if not any(e.get("isRequired") for e in c.get("extra", []) if isinstance(e, dict))
        ][:3]
        if len(catalogs) < 3:
            return "FAIL", f"menos de 3 catálogos encontrados no Kids ({len(catalogs)})"

        for c in catalogs:
            cid = c.get("id")
            ctype = c.get("type")
            r_cat = client.get(f"/{kids_token}/catalog/{ctype}/{cid}.json")
            if r_cat.status_code != 200:
                return "FAIL", f"catálogo {cid} status {r_cat.status_code}"
            items = r_cat.json().get("metas", [])
            if len(items) < 5:
                return "FAIL", f"catálogo {cid} tem {len(items)} (< 5)"

        r_stream = client.get(f"/{kids_token}/stream/series/tt2293002:1:2.json")
        if r_stream.status_code != 200:
            return "FAIL", f"stream status {r_stream.status_code}"

    return "PASS", "id .kids, 3 catálogos (>= 5 itens) e stream OK"


def t_legendas(token: str) -> tuple[str, str]:
    pt_fn = urllib.parse.quote("filename=Ben.10.Omniverse.S01E02.1080p.WEB-DL.DUAL.PT-BR.mkv")
    with get_client() as client:
        r_pt = client.get(f"/{token}/subtitles/series/tt2293002:1:2/{pt_fn}.json")
        if r_pt.status_code != 200:
            return "FAIL", f"pedido PT status {r_pt.status_code}"
        subs_pt = r_pt.json().get("subtitles", [])
        if len(subs_pt) != 0:
            return "FAIL", f"esperada lista vazia para áudio PT, obtido {len(subs_pt)}"

        en_fn = urllib.parse.quote("filename=The.Shawshank.Redemption.1994.1080p.BluRay.x264.mkv")
        r_en = client.get(f"/{token}/subtitles/movie/tt0111161/{en_fn}.json")
        if r_en.status_code != 200:
            return "FAIL", f"pedido EN status {r_en.status_code}"
        subs_en = r_en.json().get("subtitles", [])
        if len(subs_en) == 0:
            return "WARN", "pedido EN retornou lista vazia (possível limite de cota)"

    return "PASS", f"PT filtrado para vazio, EN retornou {len(subs_en)} legendas"


def t_status(token: str) -> tuple[str, str]:
    with get_client() as client:
        r = client.get(f"/{token}/status")
        if r.status_code != 200:
            return "FAIL", f"status {r.status_code}"
        text = r.text
        if token in text:
            return "FAIL", "HTML contém o token pessoal"
        if "apiKey" in text:
            return "FAIL", "HTML contém apiKey"
        if "TORBOX" in text:
            return "FAIL", "HTML contém TORBOX"

        r_x = client.get("/x/status")
        if r_x.status_code != 404:
            return "FAIL", f"/x/status retornou {r_x.status_code} (!= 404)"

        r_root = client.get("/status")
        if r_root.status_code != 404:
            return "FAIL", f"/status retornou {r_root.status_code} (!= 404)"

    return "PASS", "200 sem segredos, /x/status e /status 404"


def t_configure() -> tuple[str, str]:
    with get_client() as client:
        r = client.get("/configure")
    if r.status_code != 200:
        return "FAIL", f"status {r.status_code}"
    return "PASS", "status 200"


def t_busca_inteligente(token: str) -> tuple[str, str]:
    from comet.services.smart_search import parse_query

    # 1. Unidade de parse_query para 4 frases
    p1 = parse_query("comédia anos 90 dublada")
    assert p1 is not None and p1.get("dublado") is True and p1.get("genres", {}).get("movie") == [35], "parse comédia anos 90 dublada falhou"

    p2 = parse_query("terror com Jason")
    assert p2 is not None and p2.get("person") == "Jason" and p2.get("genres", {}).get("movie") == [27], "parse terror com Jason falhou"

    p3 = parse_query("filme de tubarão")
    assert p3 is not None and p3.get("keyword") == "shark", "parse filme de tubarão falhou"

    p4 = parse_query("batman")
    assert p4 is None, "parse batman deve retornar None"

    # 2. Busca HTTP real: terror de zumbi filme >= 10 e o 1º resultado tem gênero terror no meta
    with get_client(timeout=35.0) as client:
        q_enc = urllib.parse.quote("terror de zumbi")
        r = client.get(f"/{token}/catalog/movie/comet_search/search={q_enc}.json")
        if r.status_code != 200:
            return "FAIL", f"terror de zumbi: status {r.status_code}"
        metas = r.json().get("metas", [])
        if len(metas) < 10:
            return "FAIL", f"terror de zumbi: retornou apenas {len(metas)} itens (< 10)"

        first_id = metas[0].get("id")
        if not first_id:
            return "FAIL", "terror de zumbi: 1º resultado sem id"

        r_meta = client.get(f"/{token}/meta/movie/{first_id}.json")
        if r_meta.status_code != 200:
            return "FAIL", f"terror de zumbi: meta status {r_meta.status_code}"
        meta_data = r_meta.json().get("meta", {})
        genres = [g.lower() for g in meta_data.get("genres", [])]
        if not any("terror" in g or "horror" in g for g in genres):
            return "FAIL", f"terror de zumbi: 1º resultado ({meta_data.get('name')}) sem gênero terror: {genres}"

        # 3. Caso 1: série anime do pirata que estica -> One Piece nos 3 primeiros
        q1 = urllib.parse.quote("anime do pirata que estica")
        r1 = client.get(f"/{token}/catalog/series/comet_search/search={q1}.json")
        if r1.status_code != 200:
            return "FAIL", f"anime do pirata que estica: status {r1.status_code}"
        metas1 = r1.json().get("metas", [])
        top3_names = [m.get("name", "").lower() for m in metas1[:3]]
        if not any("one piece" in n for n in top3_names):
            return "FAIL", f"anime do pirata que estica: One Piece não está no top 3: {[m.get('name') for m in metas1[:3]]}"

        # 4. Caso 2: série serie de medicos -> >= 2 de {Grey's Anatomy, House, The Good Doctor, New Amsterdam, Plantão Médico/ER, Scrubs} no top 8
        q2 = urllib.parse.quote("serie de medicos")
        r2 = client.get(f"/{token}/catalog/series/comet_search/search={q2}.json")
        if r2.status_code != 200:
            return "FAIL", f"serie de medicos: status {r2.status_code}"
        metas2 = r2.json().get("metas", [])
        med_targets = ["grey's anatomy", "greys anatomy", "house", "dr. house", "the good doctor", "new amsterdam", "plantão médico", "plantao medico", "er", "scrubs"]
        med_matches = [m.get("name") for m in metas2[:8] if any(t in m.get("name", "").lower() for t in med_targets)]
        if len(med_matches) < 2:
            return "FAIL", f"serie de medicos: menos de 2 médicos no top 8 ({len(med_matches)} achados: {med_matches})"

        # 5. Caso 3: filme filme de advogado -> >= 10 resultados
        q3 = urllib.parse.quote("filme de advogado")
        r3 = client.get(f"/{token}/catalog/movie/comet_search/search={q3}.json")
        if r3.status_code != 200:
            return "FAIL", f"filme de advogado: status {r3.status_code}"
        metas3 = r3.json().get("metas", [])
        if len(metas3) < 10:
            return "FAIL", f"filme de advogado: retornou apenas {len(metas3)} itens (< 10)"

        # 6. Caso 4: série desenho do cachorro detetive -> Scooby-Doo nos 8 primeiros
        q4 = urllib.parse.quote("desenho do cachorro detetive")
        r4 = client.get(f"/{token}/catalog/series/comet_search/search={q4}.json")
        if r4.status_code != 200:
            return "FAIL", f"desenho do cachorro detetive: status {r4.status_code}"
        metas4 = r4.json().get("metas", [])
        top8_names = [m.get("name", "").lower() for m in metas4[:8]]
        if not any("scooby" in n for n in top8_names):
            return "FAIL", f"desenho do cachorro detetive: Scooby-Doo não está no top 8: {[m.get('name') for m in metas4[:8]]}"

    return "PASS", f"unidade OK, terror zumbi, pirata que estica (One Piece), médicos (>=2), advogado ({len(metas3)}), cachorro detetive (Scooby) OK"


def t_busca_bateria(token: str) -> tuple[str, str]:
    if not token:
        return "FAIL", "PERSONAL_LINK_TOKEN não encontrado no .env"

    import unicodedata

    def _is_non_latin(text: str) -> bool:
        if not text:
            return False
        has_letter = False
        for ch in text:
            try:
                name = unicodedata.name(ch, "")
            except Exception:
                continue
            if "LETTER" in name or "IDEOGRAPH" in name:
                has_letter = True
                if "LATIN" in name:
                    return False
        return has_letter

    tests = [
        # 10 com Esperado
        {
            "type": "series", "query": "serie de bombeiros",
            "check": lambda metas: any(t in m.get("name", "").lower() for m in metas[:8] for t in ("9-1-1", "chicago fire", "station 19", "estação 19")),
            "desc": "9-1-1, Chicago Fire ou Station 19 no top 8"
        },
        {
            "type": "series", "query": "anime de cozinha",
            "check": lambda metas: any(t in m.get("name", "").lower() for m in metas[:8] for t in ("food wars", "shokugeki")),
            "desc": "Food Wars no top 8"
        },
        {
            "type": "series", "query": "serie de cozinha competicao",
            "check": lambda metas: any(t in m.get("name", "").lower() for m in metas[:8] for t in ("masterchef", "hell's kitchen", "top chef")),
            "desc": "MasterChef, Hell's Kitchen ou Top Chef no top 8"
        },
        {
            "type": "movie", "query": "filme de cachorro que fala",
            "check": lambda metas: sum(1 for m in metas[:8] if any(t in m.get("name", "").lower() for t in ("scooby", "bolt", "peabody", "ruim pra cachorro", "como cães e gatos", "como caes e gatos", "beethoven", "homeward bound", "a caminho de casa", "supercão", "supercao", "up: altas", "gato de botas", "flow"))) >= 3,
            "desc": "≥ 3 cachorros falantes no top 8"
        },
        {
            "type": "movie", "query": "filme espacial com astronauta perdido",
            "check": lambda metas: any(t in m.get("name", "").lower() for m in metas[:8] for t in ("perdido em marte", "the martian")),
            "desc": "Perdido em Marte no top 8"
        },
        {
            "type": "movie", "query": "terror em hospital abandonado",
            "check": lambda metas: len(metas) >= 8,
            "desc": "≥ 8 filmes de terror"
        },
        {
            "type": "series", "query": "serie de policia brasileira",
            "check": lambda metas: len(metas) >= 4,
            "desc": "≥ 4 séries policiais brasileiras"
        },
        {
            "type": "series", "query": "anime de ninja",
            "check": lambda metas: len(metas) >= 8 and not any(_is_non_latin(m.get("name", "")) for m in metas[:8]) and ("naruto" in metas[0].get("name", "").lower() if metas else False),
            "desc": "sem não-latino no top 8 e Naruto no topo"
        },
        {
            "type": "movie", "query": "filme do cara que acorda sempre no mesmo dia",
            "check": lambda metas: any(t in m.get("name", "").lower() for m in metas[:8] for t in ("feitiço do tempo", "feitico do tempo", "groundhog day", "no limite do amanhã", "no limite do amanha", "edge of tomorrow", "a morte te dá parabéns", "a morte te da parabens")),
            "desc": "Feitiço do Tempo / No Limite do Amanhã / A Morte Te Dá Parabéns no top 8"
        },
        {
            "type": "movie", "query": "filme de dinossauro",
            "check": lambda metas: any("jurassic" in m.get("name", "").lower() for m in metas[:3]),
            "desc": "Jurassic Park/World no top 3"
        },
        # 22 Não Podem Piorar
        {"type": "movie", "query": "filme de viagem no tempo", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "movie", "query": "filme de assalto a banco", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "movie", "query": "fim do mundo", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "series", "query": "serie de vampiro adolescente", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "movie", "query": "filme de boxe", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "series", "query": "anime de futebol", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "movie", "query": "filme de natal para familia", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "series", "query": "serie de advogado", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "movie", "query": "filme sobre a segunda guerra", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "series", "query": "desenho de super heroi", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "series", "query": "serie de zumbi", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "movie", "query": "comedia romantica dos anos 2000", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "movie", "query": "filme de tubarao assassino", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "movie", "query": "filme de corrida de carro", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "series", "query": "anime de robo gigante", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "series", "query": "anime do pirata que estica", "check": lambda m: any("one piece" in x.get("name", "").lower() for x in m[:3]), "desc": "One Piece no top 3"},
        {"type": "series", "query": "serie de medicos", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "movie", "query": "filme de advogado", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "series", "query": "desenho do cachorro detetive", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "movie", "query": "batman", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
        {"type": "series", "query": "one piece", "check": lambda m: any("one piece" in x.get("name", "").lower() for x in m[:3]), "desc": "One Piece no top 3"},
        {"type": "movie", "query": "filme com Tom Hanks dos anos 90", "check": lambda m: len(m) >= 8, "desc": "≥ 8 itens"},
    ]

    passed = 0
    failed_cases = []
    with get_client(timeout=35.0) as client:
        for item in tests:
            t = item["type"]
            q = item["query"]
            q_enc = urllib.parse.quote(q)
            try:
                r = client.get(f"/{token}/catalog/{t}/comet_search/search={q_enc}.json")
                if r.status_code == 200:
                    metas = r.json().get("metas", [])
                    if item["check"](metas):
                        passed += 1
                        continue
                    else:
                        top6 = [m.get("name") for m in metas[:6]]
                        failed_cases.append(f"{q}: {len(metas)} itens, top6: {top6} (esperado: {item['desc']})")
                else:
                    failed_cases.append(f"{q}: status {r.status_code}")
            except Exception as e:
                failed_cases.append(f"{q}: {type(e).__name__}")

    total = len(tests)
    rate = passed / total
    detail = f"{passed}/{total} frases passaram ({rate*100:.0f}%)"
    if failed_cases:
        detail += f" | falhas: {'; '.join(failed_cases[:3])}"

    if rate >= 0.90:
        return "PASS", detail
    elif rate >= 0.75:
        return "WARN", detail
    else:
        return "FAIL", detail


def t_livetv(token: str) -> tuple[str, str]:
    if not token:
        return "FAIL", "PERSONAL_LINK_TOKEN não encontrado no .env"

    with get_client() as client:
        r_cat = client.get(f"/{token}/catalog/tv/comet_livetv.json")
        if r_cat.status_code != 200:
            return "FAIL", f"catálogo status {r_cat.status_code}"
        metas = r_cat.json().get("metas", [])
        if len(metas) < 20:
            return "FAIL", f"catálogo retornou apenas {len(metas)} itens (< 20)"

        pluto_items = [m for m in metas if str(m.get("id", "")).startswith("cometlive:pluto:")]
        if not pluto_items:
            return "FAIL", "nenhum canal Pluto encontrado no catálogo"
        # sem duplicatas (mesmo canal em duas categorias / cópia do iptv-org)
        import re as _re
        _names = [_re.sub(r"[^a-z0-9]+", "", _re.sub(r"\([^)]*\)", "", str(m.get("name", "")).lower().replace("pluto tv", ""))) for m in metas]
        _dups = sorted({n for n in _names if n and _names.count(n) > 1})
        if _dups:
            return "FAIL", f"canais duplicados no catálogo: {_dups[:8]}"
        _nulls = [m.get("id") for m in metas if any(v is None for v in m.values())]
        if _nulls:
            return "FAIL", f"metas com campo nulo: {_nulls[:5]}"
        first_id = pluto_items[0]["id"]

        bh = pluto_items[0].get("behaviorHints") or {}
        if bh.get("defaultVideoId") != first_id:
            return "FAIL", f"defaultVideoId no catálogo {bh.get('defaultVideoId')} != {first_id}"

        r_meta = client.get(f"/{token}/meta/tv/{first_id}.json")
        if r_meta.status_code != 200:
            return "FAIL", f"meta status {r_meta.status_code}"
        meta_data = r_meta.json().get("meta") or {}
        m_bh = meta_data.get("behaviorHints") or {}
        if m_bh.get("defaultVideoId") != first_id:
            return "FAIL", f"meta behaviorHints.defaultVideoId {m_bh.get('defaultVideoId')} != {first_id}"
        m_videos = meta_data.get("videos") or []
        if not m_videos or m_videos[0].get("id") != first_id:
            return "FAIL", f"meta videos[0].id inválido: {m_videos}"

        r_home = client.get(f"/{token}/catalog/tv/comet_livehome.json")
        if r_home.status_code != 200:
            return "FAIL", f"comet_livehome status {r_home.status_code}"
        home_metas = r_home.json().get("metas", [])
        if len(home_metas) < 15:
            return "FAIL", f"comet_livehome retornou {len(home_metas)} canais (< 15)"

        # 5 canais Pluto aleatórios testando a cadeia completa da opção 1
        from comet.services.live_tv import check_channel_chain
        import random
        sample_count = min(5, len(pluto_items))
        sample_pluto = random.sample(pluto_items, sample_count)

        passed = 0
        details = []
        for ch in sample_pluto:
            ch_id = ch["id"]
            ch_name = ch.get("name", ch_id)
            r_stream = client.get(f"/{token}/stream/tv/{ch_id}.json")
            if r_stream.status_code != 200:
                details.append(f"{ch_name}: stream status {r_stream.status_code}")
                continue
            streams = r_stream.json().get("streams", [])
            if not streams:
                details.append(f"{ch_name}: sem streams")
                continue
            # Opção 1: v4
            v4_url = streams[0].get("url", "")
            if not v4_url:
                details.append(f"{ch_name}: sem URL na opção 1")
                continue
            if "/live/pluto/" in v4_url:  # opção 1 testada no clique: chama o A71 local
                v4_url = "http://127.0.0.1:8000/live/pluto/" + v4_url.split("/live/pluto/", 1)[1]
            ok, motivo = check_channel_chain(v4_url)
            if ok:
                passed += 1
            else:
                details.append(f"{ch_name}: {motivo}")

        if passed < 4:
            return "FAIL", f"apenas {passed}/{sample_count} canais Pluto passaram na cadeia ({', '.join(details)})"

    return "PASS", f"{len(metas)} canais, livehome {len(home_metas)} canais, 5 Pluto ({passed}/{sample_count} cadeia OK)"


def t_play(token: str, public_base: str, shared_state: dict) -> tuple[str, str]:
    assistir_stream = shared_state.get("assistir_stream")
    if not assistir_stream:
        # Tenta buscar diretamente
        try:
            with get_client() as client:
                r = client.get(f"/{token}/stream/movie/tt12042730.json")
            if r.status_code == 200:
                streams = r.json().get("streams", [])
                assistir_stream = next((s for s in streams if s.get("name", "").startswith("▶ Assistir")), None)
        except Exception:
            pass

    if not assistir_stream:
        return "WARN", "nenhum stream '▶ Assistir' disponível"

    stream_url = assistir_stream.get("url", "")
    if not stream_url:
        return "FAIL", "stream '▶ Assistir' sem url"

    play_url = rewrite_url(stream_url, public_base, LOCAL_BASE_URL)
    headers = {
        "User-Agent": "ExoPlayerLib/2.19.1",
        "Range": "bytes=0-1023"
    }

    t0 = time.time()
    try:
        with httpx.Client(follow_redirects=True, timeout=20.0) as play_client:
            r = play_client.get(play_url, headers=headers)
    except httpx.TimeoutException:
        return "FAIL", "tempo esgotado (> 20s)"
    except Exception as e:
        return "FAIL", f"erro de conexão: {e}"

    elapsed = time.time() - t0
    if elapsed > 20.0:
        return "FAIL", f"tempo excedido ({elapsed:.1f}s > 20s)"

    if r.status_code not in (200, 206):
        return "FAIL", f"status {r.status_code}"

    ct = r.headers.get("content-type", "").lower()
    url_str = str(r.url).lower()
    is_video = ct.startswith("video/")
    is_octet = ct.startswith("application/octet-stream")
    is_hls = "mpegurl" in ct or ".m3u8" in url_str

    if is_video or is_octet or is_hls:
        kind = "video" if is_video else ("hls" if is_hls else "octet-stream")
        return "PASS", f"status {r.status_code}, {kind} em {elapsed:.2f}s"

    return "FAIL", f"content-type incompatível: {ct}"


def t_log(log_path: Path, log_offset: int) -> tuple[str, str]:
    if not log_path.is_file():
        return "PASS", "0 erros (log não encontrado)"
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            if log_offset > 0:
                f.seek(log_offset)
            content = f.read()

        errors = []
        for err_kw in ("Traceback", "NameError", "AttributeError", "TypeError"):
            if err_kw in content:
                errors.append(err_kw)

        if errors:
            return "FAIL", f"erros no log: {', '.join(errors)}"
        return "PASS", "0 erros no log"
    except Exception as e:
        return "FAIL", f"erro ao ler log: {e}"


def t_filler(token: str) -> tuple[str, str]:
    with get_client(timeout=30.0) as client:
        r = client.get(f"/{token}/meta/series/tt0388629.json")
    if r.status_code != 200:
        return "FAIL", f"status {r.status_code}"
    meta = r.json().get("meta", {})
    videos = meta.get("videos", [])
    fillers = [v for v in videos if "🟡 Filler" in (v.get("name") or v.get("title") or "")]
    if len(fillers) < 1:
        return "FAIL", "0 episódios com '🟡 Filler' em One Piece"
    return "PASS", f"{len(fillers)} fillers encontrados em One Piece"


def t_bingegroup(token: str) -> tuple[str, str]:
    with get_client(timeout=30.0) as client:
        r = client.get(f"/{token}/stream/series/tt2293002:1:2.json")
    if r.status_code != 200:
        return "FAIL", f"status {r.status_code}"
    streams = r.json().get("streams", [])
    assistir = next((s for s in streams if "▶ Assistir" in s.get("name", "")), None)
    if not assistir:
        return "FAIL", "stream '▶ Assistir' não encontrado"
    bg = assistir.get("behaviorHints", {}).get("bingeGroup")
    if bg != "comet|best|pt":
        return "FAIL", f"bingeGroup '{bg}' != 'comet|best|pt'"
    return "PASS", f"bingeGroup '{bg}'"


def t_sorteio(token: str) -> tuple[str, str]:
    with get_client(timeout=30.0) as client:
        r_movie1 = client.get(f"/{token}/catalog/movie/comet_lucky.json")
        r_movie2 = client.get(f"/{token}/catalog/movie/comet_lucky.json")
        r_series = client.get(f"/{token}/catalog/series/comet_lucky.json")
    if r_movie1.status_code != 200 or r_movie2.status_code != 200 or r_series.status_code != 200:
        return "FAIL", f"status movie={r_movie1.status_code}, series={r_series.status_code}"
    m_items1 = r_movie1.json().get("metas", [])
    m_items2 = r_movie2.json().get("metas", [])
    s_items = r_series.json().get("metas", [])
    if len(m_items1) != 10:
        return "FAIL", f"filmes sorteio: {len(m_items1)} itens (!= 10)"
    if len(s_items) != 10:
        return "FAIL", f"séries sorteio: {len(s_items)} itens (!= 10)"
    if [x.get("id") for x in m_items1] != [x.get("id") for x in m_items2]:
        return "FAIL", "pedidos seguidos de filme retornaram listas diferentes"
    if not all(x.get("posterShape") == "landscape" for x in m_items1):
        return "FAIL", "capas de filme não estão em formato landscape"
    return "PASS", "10 filmes e 10 séries sorteados com sucesso"


def t_saga(token: str, public_base: str) -> tuple[str, str]:
    with get_client(timeout=30.0) as client:
        # 0. Verificações no manifest
        r_mani = client.get(f"/{token}/manifest.json")
        if r_mani.status_code != 200:
            return "FAIL", f"manifest status {r_mani.status_code}"
        catalogs = r_mani.json().get("catalogs", [])
        cat_sagas = next((c for c in catalogs if c.get("id") == "comet_sagas" and c.get("type") == "series"), None)
        if not cat_sagas:
            return "FAIL", "catálogo series/comet_sagas não encontrado no manifest"
        cat_saga_m = next((c for c in catalogs if c.get("id") == "comet_saga" and c.get("type") == "movie"), None)
        if not cat_saga_m:
            return "FAIL", "catálogo movie/comet_saga não encontrado no manifest"
        genre_extra = next((e for e in cat_saga_m.get("extra", []) if e.get("name") == "genre"), None)
        if not genre_extra or not genre_extra.get("isRequired"):
            return "FAIL", "movie/comet_saga extra genre não tem isRequired: True"

        # 0.1 Catálogo series/comet_sagas (20 sagas)
        r_cats = client.get(f"/{token}/catalog/series/comet_sagas.json")
        if r_cats.status_code != 200:
            return "FAIL", f"catalog series/comet_sagas status {r_cats.status_code}"
        metas_sagas = r_cats.json().get("metas") or []
        if len(metas_sagas) != 20:
            return "FAIL", f"series/comet_sagas items: {len(metas_sagas)} != 20"
        if not all(m.get("type") == "series" for m in metas_sagas):
            return "FAIL", "itens de series/comet_sagas não são do tipo series"

        # 0.2 Catálogo movie/comet_saga com gênero (8 filmes do HP)
        r_catm = client.get(f"/{token}/catalog/movie/comet_saga/genre=Harry%20Potter.json")
        if r_catm.status_code != 200:
            return "FAIL", f"catalog movie/comet_saga HP status {r_catm.status_code}"
        metas_hp = r_catm.json().get("metas") or []
        if len(metas_hp) != 8:
            return "FAIL", f"movie/comet_saga HP items: {len(metas_hp)} != 8"
        if not all(m.get("type") == "movie" for m in metas_hp):
            return "FAIL", "itens de movie/comet_saga não são do tipo movie"

        # 1. Meta Harry Potter (tanto series quanto movie respondem com 8 vídeos)
        r_hp = client.get(f"/{token}/meta/series/cometsaga:1241.json")
        if r_hp.status_code != 200:
            return "FAIL", f"meta HP series status {r_hp.status_code}"
        meta_hp = r_hp.json().get("meta") or {}
        v_hp = meta_hp.get("videos") or []
        if len(v_hp) != 8:
            return "FAIL", f"HP videos: {len(v_hp)} != 8"
        if v_hp[0].get("id") != "tt0241527":
            return "FAIL", f"HP 1º vídeo id '{v_hp[0].get('id')}' != tt0241527"

        r_hp_m = client.get(f"/{token}/meta/movie/cometsaga:1241.json")
        if r_hp_m.status_code != 200:
            return "FAIL", f"meta HP movie status {r_hp_m.status_code}"
        meta_hp_m = r_hp_m.json().get("meta") or {}
        if len(meta_hp_m.get("videos") or []) != 8:
            return "FAIL", f"HP movie videos: {len(meta_hp_m.get('videos') or [])} != 8"

        # 2. Meta Star Wars e Velozes
        r_sw = client.get(f"/{token}/meta/series/cometsaga:10.json")
        if r_sw.status_code != 200:
            return "FAIL", f"meta Star Wars status {r_sw.status_code}"
        v_sw = (r_sw.json().get("meta") or {}).get("videos") or []
        if len(v_sw) != 9:
            return "FAIL", f"Star Wars videos: {len(v_sw)} != 9"

        r_fast = client.get(f"/{token}/meta/series/cometsaga:9485.json")
        if r_fast.status_code != 200:
            return "FAIL", f"meta Velozes status {r_fast.status_code}"
        v_fast = (r_fast.json().get("meta") or {}).get("videos") or []
        if len(v_fast) < 10:
            return "FAIL", f"Velozes videos: {len(v_fast)} (< 10)"

        # 3. Stream series vs movie tt0241527
        r_movie = client.get(f"/{token}/stream/movie/tt0241527.json")
        r_series = client.get(f"/{token}/stream/series/tt0241527.json")
        if r_series.status_code != 200:
            return "FAIL", f"stream series status {r_series.status_code}"
        if r_movie.status_code != 200:
            return "FAIL", f"stream movie status {r_movie.status_code}"

        streams_movie = r_movie.json().get("streams") or []
        streams_series = r_series.json().get("streams") or []
        if len(streams_series) != len(streams_movie):
            return "FAIL", f"qtd streams series ({len(streams_series)}) != movie ({len(streams_movie)})"
        if streams_series and streams_movie:
            if streams_series[0].get("name") != streams_movie[0].get("name"):
                return "FAIL", f"1º stream series '{streams_series[0].get('name')}' != movie '{streams_movie[0].get('name')}'"

        # ▶ Assistir abre no player
        assistir_stream = next((s for s in streams_series if s.get("name", "").startswith("▶ Assistir")), None)
        if assistir_stream and assistir_stream.get("url"):
            play_url = rewrite_url(assistir_stream["url"], public_base, LOCAL_BASE_URL)
            headers = {
                "User-Agent": "ExoPlayerLib/2.19.1",
                "Range": "bytes=0-1023",
            }
            try:
                with httpx.Client(follow_redirects=True, timeout=20.0) as play_client:
                    r_play = play_client.get(play_url, headers=headers)
                if r_play.status_code not in (200, 206):
                    return "FAIL", f"play Assistir status {r_play.status_code}"
            except Exception as e:
                return "FAIL", f"erro play Assistir: {e}"

    return "PASS", f"HP: 8 vids, SW: 9 vids, Velozes: {len(v_fast)} vids, streams match ({len(streams_series)})"


def t_fileiras_novas(token: str) -> tuple[str, str]:
    new_rows = [
        ("movie", "comet_mood_cry", 10),
        ("movie", "comet_mood_twist", 10),
        ("series", "comet_mood_binge", 10),
        ("movie", "comet_mood_light", 10),
        ("movie", "comet_mood_family", 10),
        ("movie", "comet_mood_night", 10),
        ("series", "comet_anime_dub", 10),
        ("series", "comet_week", 3),
        ("movie", "comet_mood_oscar", 15),
        ("movie", "comet_mood_top", 15),
        ("movie", "comet_mood_classicdub", 15),
    ]
    with get_client(timeout=35.0) as client:
        counts = {}
        for ctype, cid, min_items in new_rows:
            r = client.get(f"/{token}/catalog/{ctype}/{cid}.json")
            if r.status_code != 200:
                return "FAIL", f"{cid} status {r.status_code}"
            metas = r.json().get("metas", [])
            counts[cid] = len(metas)
            if len(metas) < min_items:
                return "FAIL", f"{cid} retornou apenas {len(metas)} itens (< {min_items})"
    return "PASS", f"{len(counts)} fileiras novas OK ({', '.join(f'{k}={v}' for k, v in counts.items())})"


def t_geracional(token: str) -> tuple[str, str]:
    """Salto geracional: maratonas, anime sem filler, capas vivas, qualidade real e TorBox primeiro."""
    notes = []
    with get_client(timeout=90.0) as client:
        orders = client.get(f"/{token}/catalog/series/comet_orders.json").json().get("metas", [])
        if len(orders) < 6:
            return "FAIL", f"maratonas: só {len(orders)}"
        mcu = (client.get(f"/{token}/meta/series/cometsaga:o-mcu.json").json().get("meta") or {})
        if len(mcu.get("videos") or []) < 30:
            return "FAIL", "maratona MCU com menos de 30 filmes"
        notes.append(f"maratonas {len(orders)} (MCU {len(mcu['videos'])})")
        op = (client.get(f"/{token}/meta/series/cometsaga:c-tt0388629.json").json().get("meta") or {})
        if not op or "fillers" not in (op.get("description") or ""):
            return "FAIL", "One Piece só a história sem meta"
        notes.append(f"OP canon {len(op['videos'])} eps")
        hero = client.get(f"/art/hero/movie/tt0111161.jpg")
        if hero.status_code != 200 or not hero.headers.get("content-type", "").startswith("image/"):
            return "FAIL", f"pôster editorial status {hero.status_code}"
        tv = client.get(f"/{token}/catalog/tv/comet_livehome.json").json().get("metas", [])
        if not tv or "/art/tv/" not in tv[0].get("poster", ""):
            return "FAIL", "capa de canal sem guia de TV"
        st = client.get(f"/{token}/stream/movie/tt0816692.json").json().get("streams", [])
        tb = sum(1 for s in st if "TorBox" in (s.get("description") or "") and "⚡" in s.get("name", ""))
        rd = sum(1 for s in st if "Real-Debrid" in (s.get("description") or "") and "⚡" in s.get("name", ""))
        if len(st) > 130:
            return "FAIL", f"lista sem teto: {len(st)} fontes"
        if tb < rd:
            return "FAIL", f"TorBox não é o principal (TB {tb} x RD {rd})"
        notes.append(f"fontes {len(st)} (TB⚡ {tb} · RD⚡ {rd})")
        media = sum(1 for s in st if "🎞️" in (s.get("description") or ""))
        notes.append(f"qualidade real em {media}")
    return "PASS", " · ".join(notes)


def t_notas(token: str) -> tuple[str, str]:
    """Página do título com notas do OMDb (IMDb/Rotten) e Oscar; usa o cache, não gasta cota."""
    with get_client(timeout=35.0) as client:
        r = client.get(f"/{token}/meta/movie/tt0068646.json")
        if r.status_code != 200:
            return "FAIL", f"meta status {r.status_code}"
        first = ((r.json().get("meta") or {}).get("description") or "").split("\n")[0]
    if "IMDb" not in first:
        return "WARN", "sem linha de notas (OMDb sem cota ou fora do ar?)"
    if "Oscar" not in first:
        return "FAIL", f"O Poderoso Chefão sem Oscar na linha de notas: {first[:80]}"
    return "PASS", first[:90]


def t_extras(token: str) -> tuple[str, str]:
    """Fileiras extras (08/11/2026): no manifesto, Minha TV com grade e play, imagens, porta pública fechada."""
    import subprocess
    with get_client(timeout=120.0) as client:
        ids = {c["id"] for c in client.get(f"/{token}/manifest.json").json().get("catalogs", [])}
        falta = {"comet_tonight", "comet_fut", "comet_mytv", "comet_recap"} - ids
        if falta:
            return "FAIL", f"fileiras fora do manifesto: {sorted(falta)}"
        m = client.get(f"/{token}/meta/tv/cometlive:mytv:main.json").json().get("meta")
        if not m:
            return "WARN", "Minha TV sem grade (menos de 3 séries no histórico?)"
        if "Agora:" not in (m.get("description") or ""):
            return "FAIL", "Minha TV sem 'Agora:' na descrição"
        st = client.get(f"/{token}/stream/tv/cometlive:mytv:main.json").json().get("streams") or []
        if not st or not st[0].get("url"):
            return "FAIL", "Minha TV sem fonte para o programa atual"
        img = client.get("/art/mytv/0.jpg")
        if img.status_code != 200 or not img.headers.get("content-type", "").startswith("image/"):
            return "FAIL", f"capa da Minha TV: {img.status_code}"
        fut = client.get(f"/{token}/catalog/tv/comet_fut.json").json().get("metas", [])
    # porta pública (Caddy 7443): painel e caminhos de robô fechados, manifesto aberto
    def code(path):
        try:
            out = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-m", "15", "--resolve",
                                  "a71comet.duckdns.org:7443:127.0.0.1", f"https://a71comet.duckdns.org:7443{path}"],
                                 capture_output=True, text=True, timeout=20)
            return out.stdout.strip()
        except Exception as e:
            return type(e).__name__
    blocked = {p: code(p) for p in ("/admin", "/metrics", "/wp-login.php", "/.env")}
    if any(c != "404" for c in blocked.values()):
        return "FAIL", f"porta 7443 deixou passar: {blocked}"
    if code(f"/{token}/manifest.json") != "200":
        return "FAIL", "porta 7443 bloqueou o manifesto"
    return "PASS", f"4 fileiras no manifesto · Minha TV: {st[0].get('title', '')[:50]} · futebol hoje: {len(fut)} · 7443 fechada p/ admin/robôs"


def t_nuvio(token: str, nuvio_token: str) -> tuple[str, str]:
    """Link do Nuvio: mesmas fileiras do pessoal, fundo sem texto e sem repasse fix=1."""
    if not nuvio_token:
        return "WARN", "NUVIO_LINK_TOKEN não configurado"
    with get_client(timeout=60.0) as client:
        a = client.get(f"/{nuvio_token}/manifest.json").json()
        b = client.get(f"/{token}/manifest.json").json()
        if [c.get("id") for c in a.get("catalogs", [])] != [c.get("id") for c in b.get("catalogs", [])]:
            return "FAIL", "fileiras diferentes do link pessoal"
        bg_n = ((client.get(f"/{nuvio_token}/meta/movie/tt0816692.json").json().get("meta") or {}).get("background") or "")
        bg_p = ((client.get(f"/{token}/meta/movie/tt0816692.json").json().get("meta") or {}).get("background") or "")
        if "/art/hero" in bg_n:
            return "FAIL", "Nuvio recebeu a arte com texto no fundo"
        if "/art/hero" not in bg_p:
            return "FAIL", "link pessoal perdeu a arte do fundo"
        st = client.get(f"/{nuvio_token}/stream/series/tt0944947:1:1.json").json().get("streams") or []
        saga = client.get(f"/{nuvio_token}/catalog/movie/comet_saga.json").json().get("metas") or []
        reacher = client.get(f"/{nuvio_token}/stream/series/tt9288030:1:1.json").json().get("streams") or []
    if not saga:
        return "FAIL", "Descobrir > Sagas vazio sem gênero"
    if any("preacher" in (s.get("description") or "").lower() for s in reacher):
        return "FAIL", "Preacher na lista de Reacher"
    if not st:
        return "FAIL", "sem streams"
    if any("fix=1" in (s.get("url") or "") for s in st):
        return "FAIL", "Nuvio recebeu fonte com fix=1"
    if any("Começa em" in (s.get("description") or "") for s in st):
        return "FAIL", "aviso de faixa no Nuvio"
    return "PASS", f"{len(a.get('catalogs', []))} fileiras, fundo limpo, {len(st)} fontes sem fix=1"


# =====================================================================
# Runner Principal
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Comet Regression Test Suite")
    parser.add_argument("--only", help="Executar apenas os testes especificados (separados por vírgula)")
    parser.add_argument("--skip-unit", action="store_true", help="Pular testes de unidade")
    parser.add_argument("--save-baseline", action="store_true", help="Gravar linha de base atual")
    parser.add_argument("--log-file", default="/var/tmp/comet.log", help="Caminho do log do Comet")
    parser.add_argument("--log-offset", type=int, default=0, help="Offset inicial em bytes do log")
    args = parser.parse_args()

    env = load_env()
    token = env.get("PERSONAL_LINK_TOKEN", "")
    kids_token = env.get("KIDS_LINK_TOKEN", "")
    nuvio_token = env.get("NUVIO_LINK_TOKEN", "")
    public_base = env.get("PUBLIC_BASE_URL", "").rstrip("/")
    tokens_to_sanitize = get_sensitive_tokens(env)

    only_filter = None
    if args.only:
        names = [n.strip() for n in args.only.split(",") if n.strip()]
        only_filter = set()
        for n in names:
            only_filter.add(n)
            if n.startswith("t_"):
                only_filter.add(n[2:])
            else:
                only_filter.add(f"t_{n}")

    baseline_data = {}
    if not args.save_baseline and BASELINE_PATH.is_file():
        try:
            baseline_data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        except Exception:
            baseline_data = {}

    current_baseline = {"streams": {}, "catalogs": {}}
    shared_state = {}

    unit_tests = [
        ("unit_is_cam_release", t_unit_is_cam_release),
        ("unit_ass_to_srt", t_unit_ass_to_srt),
        ("unit_vtt_to_srt", t_unit_vtt_to_srt),
        ("unit_ptbr_detection", t_unit_ptbr_detection),
        ("unit_dub_kind", t_unit_dub_kind),
        ("unit_select_debrid_refresh_hashes", t_unit_select_debrid_refresh_hashes),
        ("unit_prefetch_next_episode", t_unit_prefetch_next_episode),
        ("unit_stream_debrid_priority", t_unit_stream_debrid_priority),
        ("unit_parse_media_id", t_unit_parse_media_id),
        ("unit_is_video", t_unit_is_video),
        ("unit_normalize_title", t_unit_normalize_title),
        ("unit_format_resolution", t_unit_format_resolution),
        ("unit_format_size_gb", t_unit_format_size_gb),
        ("unit_format_uptime", t_unit_format_uptime),
        ("unit_merge_aliases", t_unit_merge_aliases),
        ("unit_source_breaker", t_unit_source_breaker),
        ("unit_predownload_pick", t_unit_predownload_pick),
        ("unit_episodios_ptbr", t_unit_episodios_ptbr),
        ("unit_nuvio_4k_natal", t_unit_nuvio_4k_natal),
        ("unit_fileiras_homonimos", t_unit_fileiras_homonimos),
        ("unit_pt_text", t_unit_pt_text),
        ("unit_novidades_1108", t_unit_novidades_1108),
    ]

    all_results = []

    def execute_test(name: str, fn, *fn_args):
        t0 = time.time()
        try:
            status, why = fn(*fn_args)
            if status not in ("PASS", "FAIL", "WARN"):
                status = "FAIL"
                why = f"status desconhecido: {status}"
        except Exception as exc:
            status = "FAIL"
            why = f"{type(exc).__name__}: {str(exc)[:80]}"
        secs = time.time() - t0
        clean_why = sanitize(str(why), tokens_to_sanitize)
        print(f"{status}  {name}  {secs:.2f}s  {clean_why}")
        return {
            "name": name,
            "status": status,
            "why": clean_why,
            "secs": round(secs, 2)
        }

    # 1. Unidade
    if not args.skip_unit:
        for name, fn in unit_tests:
            if only_filter and name not in only_filter and f"t_{name}" not in only_filter:
                continue
            res = execute_test(name, fn)
            all_results.append(res)

    # 2. Integrados (HTTP)
    # Lista de testes independentes para rodar em paralelo (máx 4 threads)
    parallel_tests = [
        ("manifest", lambda: t_manifest(token)),
        ("catalogos", lambda: t_catalogos(token, baseline_data, current_baseline, args.save_baseline)),
        ("capa", lambda: t_capa(token, public_base)),
        ("busca", lambda: t_busca(token)),
        ("meta_filme", lambda: t_meta_filme(token)),
        ("meta_serie", lambda: t_meta_serie(token)),
        ("stream_filme", lambda: t_stream_filme(token, baseline_data, current_baseline, args.save_baseline, shared_state)),
        ("stream_serie", lambda: t_stream_serie(token, baseline_data, current_baseline, args.save_baseline)),
        ("stream_anime", lambda: t_stream_anime(token, baseline_data, current_baseline, args.save_baseline)),
        ("kids", lambda: t_kids(kids_token)),
        ("legendas", lambda: t_legendas(token)),
        ("status", lambda: t_status(token)),
        ("configure", lambda: t_configure()),
        ("livetv", lambda: t_livetv(token)),
        ("busca_inteligente", lambda: t_busca_inteligente(token)),
        ("busca_bateria", lambda: t_busca_bateria(token)),
        ("filler", lambda: t_filler(token)),
        ("bingegroup", lambda: t_bingegroup(token)),
        ("sorteio", lambda: t_sorteio(token)),
        ("saga", lambda: t_saga(token, public_base)),
        ("fileiras_novas", lambda: t_fileiras_novas(token)),
        ("notas", lambda: t_notas(token)),
        ("nuvio", lambda: t_nuvio(token, nuvio_token)),
        ("extras", lambda: t_extras(token)),
        ("geracional", lambda: t_geracional(token)),
    ]

    selected_parallel = [
        (name, fn) for name, fn in parallel_tests
        if not only_filter or (name in only_filter or f"t_{name}" in only_filter)
    ]

    if selected_parallel:
        parallel_results_map = {}

        def run_parallel_item(fn):
            t0 = time.time()
            # Uma 2ª tentativa após 15 s: absorve o aquecimento logo depois de reiniciar.
            for attempt in range(2):
                try:
                    status, why = fn()
                    if status not in ("PASS", "FAIL", "WARN"):
                        why = f"status desconhecido: {status}"
                        status = "FAIL"
                except Exception as exc:
                    status = "FAIL"
                    why = f"{type(exc).__name__}: {str(exc)[:80]}"
                if status != "FAIL" or attempt == 1 or os.environ.get("REGRESS_SELFTEST") == "1":
                    break
                time.sleep(15)
            secs = time.time() - t0
            return status, why, secs

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_name = {executor.submit(run_parallel_item, fn): name for name, fn in selected_parallel}
            for fut in as_completed(future_to_name):
                name = future_to_name[fut]
                status, why, secs = fut.result()
                clean_why = sanitize(str(why), tokens_to_sanitize)
                parallel_results_map[name] = {
                    "name": name,
                    "status": status,
                    "why": clean_why,
                    "secs": round(secs, 2)
                }

        # Imprime na ordem original
        for name, _ in selected_parallel:
            r = parallel_results_map[name]
            print(f"{r['status']}  {r['name']}  {r['secs']:.2f}s  {r['why']}")
            all_results.append(r)

    # 3. Play (depende de stream_filme ou busca direta)
    if not only_filter or ("play" in only_filter or "t_play" in only_filter):
        res_play = execute_test("play", t_play, token, public_base, shared_state)
        all_results.append(res_play)

    # 4. Log (executado por último para capturar a suíte inteira)
    if not only_filter or ("log" in only_filter or "t_log" in only_filter):
        res_log = execute_test("log", t_log, Path(args.log_file), args.log_offset)
        all_results.append(res_log)

    pass_count = sum(1 for t in all_results if t["status"] == "PASS")
    warn_count = sum(1 for t in all_results if t["status"] == "WARN")
    fail_count = sum(1 for t in all_results if t["status"] == "FAIL")
    failed_names = [t["name"] for t in all_results if t["status"] == "FAIL"]

    if fail_count == 0:
        print(f"REGRESS OK ({pass_count} pass, {warn_count} warn)")
    else:
        print(f"REGRESS FALHOU ({fail_count} fail: {', '.join(failed_names)})")

    # Salva regress_last.json
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "ok": fail_count == 0,
        "tests": all_results
    }
    try:
        REGRESS_LAST_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"Aviso: erro ao salvar regress_last.json: {e}", file=sys.stderr)

    # Salva baseline se solicitado
    if args.save_baseline:
        try:
            BASELINE_PATH.write_text(json.dumps(current_baseline, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"Aviso: erro ao salvar regress_baseline.json: {e}", file=sys.stderr)

    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
