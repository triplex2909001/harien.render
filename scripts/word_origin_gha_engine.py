#!/usr/bin/env python3
"""Word Origin 2D Engine for GitHub Actions (OmniVoice `harien.omni` & Hyperframes `harien.render`).
Google Drive (`aleron.dt:`) is the Single Source of Truth (SSOT):
- Posts Folder ID: 19p_SWDErDYluix6g6Qg9f8lCCmALHjMQ
- Hanario Root Folder ID: 1JA4bGZ4pMn0BquMAOTyp8geDsbTyF80w
Rule: File length <= 150 lines (AGENTS.md).
"""
import datetime, json, os, re, shutil, subprocess

POSTS_FOLDER_ID = os.environ.get("GDRIVE_POSTS_FOLDER_ID", "19p_SWDErDYluix6g6Qg9f8lCCmALHjMQ")
HANARIO_ROOT_ID = os.environ.get("GDRIVE_HANARIO_FOLDER_ID", "1JA4bGZ4pMn0BquMAOTyp8geDsbTyF80w")
SCENE_KEYS = ["s01", "s02", "s03a", "s03b", "s04"]


def get_rclone_remote() -> str:
    if not shutil.which("rclone"):
        return ""
    out = subprocess.run(["rclone", "listremotes"], capture_output=True, text=True).stdout.splitlines()
    for pref in ("aleron.dt:", "vpsg24gb.aleron.dt:"):
        if pref in out:
            return pref.rstrip(":")
    return next((l.strip().rstrip(":") for l in out if l.strip().endswith(":")), "")


def gdrive_pull_post(remote: str, post_id: str, rel_path: str, local_path: str, is_dir: bool = False) -> bool:
    if not remote:
        return os.path.exists(local_path)
    os.makedirs(local_path if is_dir else os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
    cmd = ["rclone", "copy" if is_dir else "copyto", f"{remote}:{post_id}/{rel_path}", local_path, "--drive-root-folder-id", POSTS_FOLDER_ID]
    return subprocess.run(cmd, capture_output=True).returncode == 0


def gdrive_push_post(remote: str, post_id: str, local_path: str, rel_path: str, is_dir: bool = False) -> bool:
    if not (remote and os.path.exists(local_path)):
        return False
    cmd = ["rclone", "copy" if is_dir else "copyto", local_path, f"{remote}:{post_id}/{rel_path}", "--drive-root-folder-id", POSTS_FOLDER_ID]
    return subprocess.run(cmd, capture_output=True).returncode == 0


def resolve_speakers_by_level(level: str) -> dict:
    lv = (level or "B2").upper().strip()
    if lv in ("A1", "A2", "A1-A2"):
        return {"mode": "Bilingual", "s01": ("rio", "en"), "s02": ("thuy_duong", "vi"), "s03a": ("rio", "en"), "s03b": ("thuy_duong", "vi"), "s04": ("rio", "en")}
    if lv == "B1":
        return {"mode": "Bilingual", "s01": ("bella", "en"), "s02": ("thuy_duong", "vi"), "s03a": ("bella", "en"), "s03b": ("thuy_duong", "vi"), "s04": ("bella", "en")}
    return {"mode": "Monolingual_EN", "s01": ("hana", "en"), "s02": ("bella", "en"), "s03a": ("bella", "en"), "s03b": ("bella", "en"), "s04": ("hana", "en")}


REF_VOICE_MAP = {
    "bella": ("assets/voice_samples/bella_ref.wav", "assets/voice_samples/bella_ref.txt"),
    "hana": ("assets/voice_samples/hana_ref.wav", "assets/voice_samples/hana_ref.txt"),
    "rio": ("assets/voice_samples/rio_ref.wav", "assets/voice_samples/rio_ref.txt"),
    "thuy_duong": ("assets/voice_samples/thuy_duong.wav", "assets/voice_samples/thuy_duong.txt"),
}


def strip_speaker_tag(raw_text: str) -> str:
    lines = [l.strip() for l in (raw_text or "").splitlines() if l.strip() and not l.strip().upper().startswith("[TITLE]")]
    joined = " ".join(lines)
    return re.sub(r"^\[[^\]]+\]\s*:\s*", "", joined).strip()


def _synth_omnivoice_scene(spk: str, lang: str, text: str, wav_p: str):
    ref_wav, ref_txt_p = REF_VOICE_MAP.get(spk, REF_VOICE_MAP["bella"])
    ref_txt = open(ref_txt_p, encoding="utf-8").read().strip() if os.path.exists(ref_txt_p) else ""
    try:
        from scripts.omnivoice_hf_client import _synth_one, _upload_ref
        rpath = _upload_ref(ref_wav, spk)
        _synth_one(rpath, ref_txt, {"id": spk, "text": text, "lang": lang, "speed": 0.95}, wav_p)
        if os.path.exists(wav_p) and os.path.getsize(wav_p) > 1000:
            return
    except Exception as e:
        print(f"[OmniVoice HF Space fallback to local k2-fsa/OmniVoice] {e}", flush=True)
    from scripts.colab_worker_payload import run_tts
    run_tts(text, wav_p, ref_audio=ref_wav, ref_text=ref_txt)


def run_omnivoice_word_origin(post_id: str, wdir: str, level: str = "B2", force: bool = False) -> list:
    """GitHub Actions Engine 1 (`harien.omni`): Pulls 00_post_manifest.json from GDrive SSOT,
    synthesizes 01_audio/s01..s04.wav via k2-fsa/OmniVoice, and syncs back to GDrive Posts/<post_id>/01_audio/."""
    remote = get_rclone_remote()
    os.makedirs(wdir, exist_ok=True)
    man_path = os.path.join(wdir, "00_post_manifest.json")
    gdrive_pull_post(remote, post_id, "00_post_manifest.json", man_path)
    manifest = json.load(open(man_path, encoding="utf-8")) if os.path.exists(man_path) else {"post_id": post_id, "level": level}
    eff_level = manifest.get("level") or level
    spk_cfg = resolve_speakers_by_level(eff_level)
    adir = os.path.join(wdir, "01_audio")
    os.makedirs(adir, exist_ok=True)
    if not force:
        gdrive_pull_post(remote, post_id, "01_audio", adir, is_dir=True)

    created = []
    for sk in SCENE_KEYS:
        wav_p = os.path.join(adir, f"{sk}.wav")
        if force or not (os.path.exists(wav_p) and os.path.getsize(wav_p) > 1000):
            spk, lang = spk_cfg[sk]
            text = strip_speaker_tag(manifest.get(sk, f"Word Origin scene {sk} for {post_id}."))
            print(f"[OmniVoice 2D] Synthesizing {post_id}/{sk}.wav ({spk}, {lang}): {text}", flush=True)
            _synth_omnivoice_scene(spk, lang, text, wav_p)
        if os.path.exists(wav_p):
            gdrive_push_post(remote, post_id, wav_p, f"01_audio/{sk}.wav")
            created.append(f"01_audio/{sk}.wav")

    ckpt = {"post_id": post_id, "engine": "OmniVoice@GitHubActions(harien.omni)", "level": eff_level, "pairing": spk_cfg["mode"], "files": created, "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    ckpt_p = os.path.join(adir, "omnivoice_checkpoint.json")
    json.dump(ckpt, open(ckpt_p, "w", encoding="utf-8"), indent=2)
    gdrive_push_post(remote, post_id, ckpt_p, "01_audio/omnivoice_checkpoint.json")
    return created


def run_hyperframes_word_origin(post_id: str, wdir: str, level: str = "B2") -> dict:
    """GitHub Actions Engine 2 (`harien.render`): Pulls 00_post_manifest.json + 01_audio/ + 03_videos_raw/
    (generated by GFlow on vpsg24gb) from GDrive SSOT, renders Hyperframes 2D Karaoke & Black Note End Card,
    and pushes Final MP4 + Cover PNG back to GDrive SSOT Posts/<post_id>/."""
    remote = get_rclone_remote()
    os.makedirs(wdir, exist_ok=True)
    for sub in ("01_audio", "02_keyframes_2d", "03_videos_raw"):
        gdrive_pull_post(remote, post_id, sub, os.path.join(wdir, sub), is_dir=True)
    man_path = os.path.join(wdir, "00_post_manifest.json")
    gdrive_pull_post(remote, post_id, "00_post_manifest.json", man_path)
    manifest = json.load(open(man_path, encoding="utf-8")) if os.path.exists(man_path) else {"post_id": post_id, "level": level, "main_word": post_id.split("_")[-1]}
    word = (manifest.get("main_word") or post_id.split("_")[-1]).capitalize()
    eff_lv = (manifest.get("level") or level).upper()
    out_mp4 = os.path.join(wdir, f"WordOrigin_{eff_lv}_{word}_V2_Karaoke_2D.mp4")
    cov_png = os.path.join(wdir, f"Cover_{word}_{eff_lv}_V2_TOV.png")

    builder = "scripts/build_quarantine_b2_v2_karaoke.py"
    if os.path.exists(builder):
        subprocess.run(["python3", builder, "--manifest", man_path, "--workdir", wdir, "--out", out_mp4], check=False)
    if os.path.exists(out_mp4):
        gdrive_push_post(remote, post_id, out_mp4, os.path.basename(out_mp4))
    if os.path.exists(cov_png):
        gdrive_push_post(remote, post_id, cov_png, os.path.basename(cov_png))
    ckpt = {"post_id": post_id, "engine": "Hyperframes@GitHubActions(harien.render)", "video": os.path.basename(out_mp4), "cover": os.path.basename(cov_png), "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    ckpt_p = os.path.join(wdir, "hyperframes_checkpoint.json")
    json.dump(ckpt, open(ckpt_p, "w", encoding="utf-8"), indent=2)
    gdrive_push_post(remote, post_id, ckpt_p, "hyperframes_checkpoint.json")
    return {"body_raw": out_mp4, "cover": cov_png}
