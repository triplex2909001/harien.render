#!/usr/bin/env python3
"""Zero-Dependency OmniVoice Client via k2-fsa-omnivoice.hf.space Gradio API.
Synthesizes Zero-Shot Voice Clones (Thuy Duong VI & Bella EN) on CPU VMs (Muse / VPS)
without requiring local GPU or PyTorch installation. Rule: <= 150 lines.
"""
import concurrent.futures, json, os, subprocess, time, urllib.request

HF_SPACE = "https://k2-fsa-omnivoice.hf.space"


def _prepare_padded_ref(ref_wav: str, tag: str) -> str:
    out_ref = os.path.join(os.environ.get("TMPDIR", "/tmp"), f"omni_ref_pad_{tag}.wav")
    subprocess.check_call([
        "ffmpeg", "-y", "-i", ref_wav,
        "-af", "apad=pad_dur=0.45",
        "-ar", "24000", "-ac", "1", out_ref
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_ref


def _upload_ref(ref_wav: str, tag: str) -> str:
    padded = _prepare_padded_ref(ref_wav, tag)
    out = subprocess.check_output([
        "curl", "-sS", "--retry", "3", "-X", "POST",
        f"{HF_SPACE}/gradio_api/upload",
        "-F", f"files=@{padded}"
    ]).decode("utf-8")
    return json.loads(out)[0]


def _synth_one(rpath: str, ref_txt: str, item: dict, out_wav: str) -> str:
    ctext = item["text"].strip()
    padded_text = ctext if ctext.endswith("?") else f"{ctext.rstrip('.!')}..."
    lang_label = "Vietnamese" if item.get("lang") == "vi" else "English"
    payload = {
        "data": [
            padded_text, lang_label,
            {"path": rpath, "meta": {"_type": "gradio.FileData"}},
            ref_txt, "", 32, 2.0, True, float(item.get("speed", 0.95)), None, True, True
        ]
    }
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                f"{HF_SPACE}/gradio_api/call/_clone_fn",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            ev_id = json.loads(urllib.request.urlopen(req, timeout=25).read().decode("utf-8"))["event_id"]
            file_url = None
            with urllib.request.urlopen(f"{HF_SPACE}/gradio_api/call/_clone_fn/{ev_id}", timeout=90) as stream:
                for raw_line in stream:
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if isinstance(data, list) and data and isinstance(data[0], dict):
                            file_url = data[0].get("url") or f"{HF_SPACE}/gradio_api/file={data[0]['path']}"
            if not file_url:
                raise RuntimeError(f"No audio URL returned for {item['id']}")
            raw_wav = f"{out_wav}.raw.wav"
            urllib.request.urlretrieve(file_url, raw_wav)
            subprocess.check_call([
                "ffmpeg", "-y", "-i", raw_wav,
                "-af", "apad=pad_dur=1.0",
                "-ar", "24000", "-ac", "1", out_wav
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.remove(raw_wav)
            return out_wav
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    return out_wav


def synthesize_batch_hf(ref_wav: str, ref_txt: str, cache_dir: str, needed: list, tag: str, max_workers: int = 2) -> bool:
    os.makedirs(cache_dir, exist_ok=True)
    missing = [it for it in needed if not os.path.exists(os.path.join(cache_dir, f"{it['id']}.wav"))]
    if not missing:
        return True
    print(f"[OmniVoice-HF] Uploading reference {ref_wav} for {tag} ({len(missing)} clips)...", flush=True)
    rpath = _upload_ref(ref_wav, tag)
    t0 = time.time()
    def _job(it):
        out_w = os.path.join(cache_dir, f"{it['id']}.wav")
        _synth_one(rpath, ref_txt, it, out_w)
        print(f"  [OK] {tag} -> {it['id']}.wav ({os.path.getsize(out_w)}B): {it['text']}", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        list(ex.map(_job, missing))
    print(f"[OmniVoice-HF] Completed {len(missing)} clips for {tag} in {time.time()-t0:.1f}s", flush=True)
    return True
