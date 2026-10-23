#!/usr/bin/env python3
import argparse, datetime, json, os, shutil, subprocess, sys, tarfile


def get_remote() -> str:
    if not shutil.which("rclone"):
        return ""
    res = subprocess.run(["rclone", "listremotes"], capture_output=True, text=True)
    return next((l.strip().rstrip(":") for l in res.stdout.splitlines() if l.strip().endswith(":")), "")


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


def ensure_engine(remote: str, prod_id: str):
    if os.path.exists("scripts/gha_engine_helper.py"):
        return
    tar_p = "/tmp/engine_bundle.tar.gz"
    if not gdrive_pull(remote, prod_id, "_ENGINE/engine_bundle.tar.gz", tar_p):
        raise RuntimeError("Failed to pull _ENGINE/engine_bundle.tar.gz from PRODUCTION")
    with tarfile.open(tar_p, "r:gz") as tf:
        tf.extractall(".")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep-id", default=os.environ.get("EP_ID", "T01_EP003_B1"))
    ap.add_argument("--level", default=os.environ.get("LEVEL", "B1"))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    ep_id, prod_id, remote = args.ep_id, os.environ.get("GDRIVE_PRODUCTION_FOLDER_ID", "").strip(), get_remote()
    ensure_engine(remote, prod_id)
    sys.path.insert(0, os.getcwd())
    from scripts.gha_engine_helper import render_template_body_and_cover_ui

    wdir = os.path.join("workspace", ep_id)
    os.makedirs(wdir, exist_ok=True)
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
