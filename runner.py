#!/usr/bin/env python3
"""HanaRio English HTML5 & Hyperframes Renderer (`triplex2909001/harien.render`).
Supports BOTH:
  1. 3D Templates (`T01`–`T08`, e.g. `T01_EP003_B1`) -> `frames/ui_overlay.png`, `cover_flow/flow_raw.mp4`, `body_raw.mp4`
  2. 2D Word Origin (`POST_...`, e.g. `POST_002_SALARY`) -> 9:16 Karaoke + Black Note CTA End Card on GDrive SSOT
Rule: File length <= 150 lines (AGENTS.md).
"""
import argparse, datetime, json, os, shutil, subprocess, sys, tarfile, urllib.parse, urllib.request

DEFAULT_PROD_ID = "1n159pEnGwSzmTA3A0Q_Twa1qWx6PWL2a"
FALLBACK_ENGINE_IDS = ("1n159pEnGwSzmTA3A0Q_Twa1qWx6PWL2a", "1MXWYrQCwish5gBWwIkYnm1y9Son41Gya")
WORD_ORIGIN_SHEET_ID = "1-kRNOm1qj8XGDpayafESy2vkhC6KUNSDB2ApgZjfaiM"


def get_remote() -> str:
    if not shutil.which("rclone"):
        return ""
    out = [l.strip() for l in subprocess.run(["rclone", "listremotes"], capture_output=True, text=True).stdout.splitlines() if l.strip().endswith(":")]
    for pref in ("aleron.dt:", "vpsg24gb.aleron.dt:"):
        if pref in out:
            return pref.rstrip(":")
    return out[0].rstrip(":") if out else ""


def rclone_args(prod_id: str) -> list:
    return ["--drive-root-folder-id", prod_id] if prod_id else []


def gdrive_exists(remote: str, prod_id: str, rel_path: str) -> bool:
    if not (remote and prod_id):
        return False
    res = subprocess.run(["rclone", "lsf", f"{remote}:/{rel_path}", *rclone_args(prod_id)], capture_output=True, text=True)
    return res.returncode == 0 and bool(res.stdout.strip())


def gdrive_pull(remote: str, prod_id: str, rel_path: str, local_path: str, is_dir: bool = False) -> bool:
    if not (remote and prod_id):
        return os.path.exists(local_path)
    os.makedirs(local_path if is_dir else os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
    op = "copy" if is_dir else "copyto"
    return subprocess.run(["rclone", op, f"{remote}:/{rel_path}", local_path, *rclone_args(prod_id)], capture_output=True).returncode == 0


def gdrive_push(remote: str, prod_id: str, local_path: str, rel_path: str) -> bool:
    if not (remote and prod_id and os.path.exists(local_path)):
        return False
    return subprocess.run(["rclone", "copyto", local_path, f"{remote}:/{rel_path}", *rclone_args(prod_id)], capture_output=True).returncode == 0


def ensure_engine(remote: str, prod_id: str, ep_id: str):
    if ep_id.upper().startswith("POST_") and os.path.exists("scripts/word_origin_gha_engine.py"):
        return
    if os.path.exists("studio/outputs") and os.path.exists("scripts/gha_engine_helper.py"):
        return
    tar_p = "/tmp/engine_bundle.tar.gz"
    pulled = False
    for fid in dict.fromkeys([prod_id, *FALLBACK_ENGINE_IDS]):
        if fid and gdrive_pull(remote, fid, "_ENGINE/engine_bundle.tar.gz", tar_p):
            pulled = True
            break
    if not pulled:
        raise RuntimeError("Failed to pull _ENGINE/engine_bundle.tar.gz from PRODUCTION")
    with tarfile.open(tar_p, "r:gz") as tf:
        tf.extractall(".")


def update_word_origin_sheet_status(post_id: str, status_str: str):
    try:
        import configparser
        cp = configparser.ConfigParser()
        cp.read(os.path.expanduser("~/.config/rclone/rclone.conf"))
        sec = "aleron.dt" if "aleron.dt" in cp else (cp.sections()[0] if cp.sections() else "")
        if not sec:
            return
        tok = json.loads(cp[sec]["token"])["access_token"]
        hdrs = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
        rng = urllib.parse.quote("'WORD ORIGIN'!A1:A30")
        rows = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://sheets.googleapis.com/v4/spreadsheets/{WORD_ORIGIN_SHEET_ID}/values/{rng}", headers=hdrs), timeout=15).read().decode()).get("values", [])
        for idx, r in enumerate(rows, 1):
            if r and str(r[0]).strip() == post_id:
                wr = urllib.parse.quote(f"'WORD ORIGIN'!N{idx}")
                urllib.request.urlopen(urllib.request.Request(f"https://sheets.googleapis.com/v4/spreadsheets/{WORD_ORIGIN_SHEET_ID}/values/{wr}?valueInputOption=USER_ENTERED", data=json.dumps({"values": [[status_str]]}).encode(), method="PUT", headers=hdrs), timeout=15)
                break
    except Exception as e:
        print(f"[Sheet Update Warning] {e}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep-id", default=os.environ.get("EP_ID", "T01_EP001_A1"))
    ap.add_argument("--level", default=os.environ.get("LEVEL", "A1"))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    ep_id = args.ep_id.strip()
    prod_id = os.environ.get("GDRIVE_PRODUCTION_FOLDER_ID", "").strip() or DEFAULT_PROD_ID
    remote = get_remote()
    ensure_engine(remote, prod_id, ep_id)
    sys.path.insert(0, os.getcwd())

    wdir = os.path.join("workspace", ep_id)
    os.makedirs(wdir, exist_ok=True)

    # Branch 1: Word Origin 2D (POST_...)
    if ep_id.upper().startswith("POST_"):
        from scripts.word_origin_gha_engine import run_hyperframes_word_origin
        out = run_hyperframes_word_origin(ep_id, wdir, args.level)
        update_word_origin_sheet_status(ep_id, "HYPERFRAMES_GHA_DONE")
        print(f"[PASS] harien.render completed Word Origin 2D -> {out}", flush=True)
        return

    # Branch 2: 3D Templates (T01–T08)
    from scripts.gha_engine_helper import render_template_body_and_cover_ui
    gdrive_pull(remote, prod_id, f"{ep_id}/voice", os.path.join(wdir, "voice"), is_dir=True)

    targets = [("frames/ui_overlay.png", f"{ep_id}/frames/ui_overlay.png"), ("cover_flow/flow_raw.mp4", f"{ep_id}/cover_flow/flow_raw.mp4"), ("body_raw.mp4", f"{ep_id}/body_raw.mp4")]
    if not args.force and all(gdrive_exists(remote, prod_id, r) for _, r in targets):
        for lrel, rpath in targets:
            print(f"[SKIP - ALREADY ON GDRIVE] {rpath}")
            gdrive_pull(remote, prod_id, rpath, os.path.join(wdir, lrel))
        return

    out = render_template_body_and_cover_ui(ep_id, wdir, args.level)
    ckpt = {"ep_id": ep_id, "engine": "HTML5-Template-T01-T08-LiveCoverUI", "files": [], "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    for lrel, rpath in targets:
        lpath = os.path.join(wdir, lrel)
        pushed = gdrive_push(remote, prod_id, lpath, rpath)
        print(f"[RENDER SAVED TO GDRIVE={pushed}] {rpath}")
        ckpt["files"].append(lrel)
    ckpt_local = os.path.join(wdir, "render_checkpoint.json")
    json.dump(ckpt, open(ckpt_local, "w", encoding="utf-8"), indent=2)
    gdrive_push(remote, prod_id, ckpt_local, f"{ep_id}/render_checkpoint.json")
    print(f"[PASS] harien.render completed template HTML5 body & transparent UI overlay -> {out['body_raw']}")


if __name__ == "__main__":
    main()
