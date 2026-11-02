import asyncio
import io
import struct
from aiohttp import web
from comet.services.audio_probe import probe_audio

def encode_vint(val: int) -> bytes:
    if val < 0x7F:
        return bytes([0x80 | val])
    elif val < 0x3FFF:
        return bytes([0x40 | (val >> 8), val & 0xFF])
    elif val < 0x1FFFFF:
        return bytes([0x20 | (val >> 16), (val >> 8) & 0xFF, val & 0xFF])
    elif val < 0x0FFFFFFF:
        return bytes([0x10 | (val >> 24), (val >> 16) & 0xFF, (val >> 8) & 0xFF, val & 0xFF])
    else:
        raise ValueError("Val too large for vint")

def make_ebml_element(eid_bytes: bytes, data: bytes) -> bytes:
    size_bytes = encode_vint(len(data))
    return eid_bytes + size_bytes + data

def build_minimal_mkv() -> bytes:
    ebml_header = make_ebml_element(
        b"\x1a\x45\xdf\xa3",
        make_ebml_element(b"\x42\x86", b"\x01") +
        make_ebml_element(b"\x42\xf7", b"\x01") +
        make_ebml_element(b"\x42\xf2", b"\x04") +
        make_ebml_element(b"\x42\xf3", b"\x08") +
        make_ebml_element(b"\x42\x82", b"matroska")
    )
    # Track 1: video
    t1 = make_ebml_element(
        b"\xae",
        make_ebml_element(b"\xd7", b"\x01") +
        make_ebml_element(b"\x83", b"\x01") +
        make_ebml_element(b"\x86", b"V_MPEG4/ISO/AVC")
    )
    # Track 2: audio por
    t2 = make_ebml_element(
        b"\xae",
        make_ebml_element(b"\xd7", b"\x02") +
        make_ebml_element(b"\x83", b"\x02") +
        make_ebml_element(b"\x86", b"A_AAC") +
        make_ebml_element(b"\x22\xb5\x9c", b"por") +
        make_ebml_element(b"\x53\x6e", "Português".encode("utf-8"))
    )
    # Track 3: audio eng
    t3 = make_ebml_element(
        b"\xae",
        make_ebml_element(b"\xd7", b"\x03") +
        make_ebml_element(b"\x83", b"\x02") +
        make_ebml_element(b"\x86", b"A_AAC") +
        make_ebml_element(b"\x22\xb5\x9c", b"eng") +
        make_ebml_element(b"\x53\x6e", b"English")
    )
    tracks_elem = make_ebml_element(b"\x16\x54\xae\x6b", t1 + t2 + t3)
    cluster_elem = make_ebml_element(b"\x1f\x43\xb6\x75", b"\xe7\x01\x00")
    segment_elem = make_ebml_element(b"\x18\x53\x80\x67", tracks_elem + cluster_elem)
    return ebml_header + segment_elem

def pack_mp4_lang(code: str) -> int:
    b = code.encode("ascii")
    c0 = (b[0] - 0x60) & 0x1F
    c1 = (b[1] - 0x60) & 0x1F
    c2 = (b[2] - 0x60) & 0x1F
    return (c0 << 10) | (c1 << 5) | c2

def make_box(box_type: bytes, payload: bytes) -> bytes:
    length = len(payload) + 8
    return struct.pack(">I", length) + box_type + payload

def build_minimal_mp4() -> bytes:
    ftyp = make_box(b"ftyp", b"isom\x00\x00\x02\x00isommp41")
    # trak 1 (por audio)
    hdlr_por = make_box(b"hdlr", b"\x00\x00\x00\x00\x00\x00\x00\x00soun\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00SoundHandler\x00")
    lang_por = pack_mp4_lang("por")
    mdhd_por = make_box(b"mdhd", b"\x00\x00\x00\x00" + (b"\x00" * 8) + struct.pack(">I", 1000) + struct.pack(">I", 1000) + struct.pack(">H", lang_por) + b"\x00\x00")
    mdia_por = make_box(b"mdia", mdhd_por + hdlr_por)
    trak_por = make_box(b"trak", mdia_por)

    # trak 2 (eng audio)
    hdlr_eng = make_box(b"hdlr", b"\x00\x00\x00\x00\x00\x00\x00\x00soun\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00SoundHandler\x00")
    lang_eng = pack_mp4_lang("eng")
    mdhd_eng = make_box(b"mdhd", b"\x00\x00\x00\x00" + (b"\x00" * 8) + struct.pack(">I", 1000) + struct.pack(">I", 1000) + struct.pack(">H", lang_eng) + b"\x00\x00")
    mdia_eng = make_box(b"mdia", mdhd_eng + hdlr_eng)
    trak_eng = make_box(b"trak", mdia_eng)

    moov = make_box(b"moov", trak_por + trak_eng)
    return ftyp + moov

async def main():
    mkv_data = build_minimal_mkv()
    mp4_data = build_minimal_mp4()

    async def handle_mkv(request):
        range_header = request.headers.get("Range")
        data = mkv_data
        total_len = len(data)
        if range_header and range_header.startswith("bytes="):
            r = range_header[6:].split("-")
            start = int(r[0]) if r[0] else 0
            end = int(r[1]) if r[1] else total_len - 1
            chunk = data[start:end+1]
            return web.Response(
                body=chunk,
                status=206,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{total_len}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(len(chunk)),
                    "Content-Type": "video/x-matroska",
                }
            )
        return web.Response(body=data, headers={"Content-Length": str(len(data))})

    async def handle_mp4(request):
        range_header = request.headers.get("Range")
        data = mp4_data
        total_len = len(data)
        if range_header and range_header.startswith("bytes="):
            r = range_header[6:].split("-")
            start = int(r[0]) if r[0] else 0
            end = int(r[1]) if r[1] else total_len - 1
            chunk = data[start:end+1]
            return web.Response(
                body=chunk,
                status=206,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{total_len}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(len(chunk)),
                    "Content-Type": "video/mp4",
                }
            )
        return web.Response(body=data, headers={"Content-Length": str(len(data))})

    app = web.Application()
    app.router.add_get("/test.mkv", handle_mkv)
    app.router.add_get("/test.mp4", handle_mp4)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 59123)
    await site.start()

    try:
        # Test MKV
        mkv_res = await probe_audio("http://127.0.0.1:59123/test.mkv")
        print("MKV probe result:", mkv_res)
        assert mkv_res is not None, "MKV probe returned None"
        assert len(mkv_res) == 2, f"MKV expected 2 tracks, got {len(mkv_res)}"
        assert mkv_res[0]["lang"] == "por", f"MKV track 0 expected 'por', got {mkv_res[0]['lang']}"
        assert mkv_res[1]["lang"] == "eng", f"MKV track 1 expected 'eng', got {mkv_res[1]['lang']}"

        # Test MP4
        mp4_res = await probe_audio("http://127.0.0.1:59123/test.mp4")
        print("MP4 probe result:", mp4_res)
        assert mp4_res is not None, "MP4 probe returned None"
        assert len(mp4_res) == 2, f"MP4 expected 2 tracks, got {len(mp4_res)}"
        assert mp4_res[0]["lang"] == "por", f"MP4 track 0 expected 'por', got {mp4_res[0]['lang']}"
        assert mp4_res[1]["lang"] == "eng", f"MP4 track 1 expected 'eng', got {mp4_res[1]['lang']}"

        print("UNIT TEST OK")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
