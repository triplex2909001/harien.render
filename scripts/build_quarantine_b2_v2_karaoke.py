#!/usr/bin/env python3
"""Build Word Origin: QUARANTINE V2 (Dialogue Lip-Sync for Bella & Hana, Silent Historical B-Roll).
- Mascot scenes (`s01`, `s02`, `s04` -> `lip_sync=True`): Bella & Hana actively speak with clause-synced
  lip movement matching the OmniVoice voiceover (`q_01_hana.wav`, `q_02_bella.wav`, `q_04_hana.wav`).
- Historical illustrations (`s03a`, `s03b` -> `lip_sync=False`): atmospheric B-roll only.
Rule: File length <= 150 lines (AGENTS.md).
"""
import os, subprocess
from PIL import Image, ImageDraw
from word_origin_lipsync import build_lipsynced_scene_video
from word_origin_overlays import (
    ASSETS_DIR, BASE_DIR, COVER_PAINTED, LOGO_PNG, SERIF_BOLD, SERIF_REG,
    draw_karaoke_eng_sub, draw_top_header_and_logo, fnt, make_static_top_overlay,
)


def _pick_vid(talk_name: str, orig_name: str) -> str:
    tp = os.path.join(ASSETS_DIR, talk_name)
    return tp if os.path.exists(tp) else os.path.join(ASSETS_DIR, orig_name)


def get_scenes() -> list:
    return [
        {
            "id": "s01", "lip_sync": True, "y_shift": 115, "use_painted_main": True,
            "main_word": "QUARANTINE", "main_sub": "WHY DOES IT MEAN 40 DAYS?",
            "en_lines": ["Teacher Bella, why does the word quarantine", "start with quar—almost like a quarter", "or the number four?"],
            "vi_lines": ["Cô Bella ơi, sao từ “quarantine” lại bắt đầu bằng “quar-”—", "nghe gần giống một phần tư hay số 4 vậy ạ?"],
            "wav": f"{ASSETS_DIR}/q_01_hana.wav", "ss": 0.0, "dur": None,
            "vid": _pick_vid("quarantine_v2_s01_talk_9x16-001.mp4", "quarantine_v2_s01_video-001.mp4"),
            "talk_win": None,
        },
        {
            "id": "s02", "lip_sync": True, "y_shift": 175, "use_painted_main": False,
            "main_word": "QUARANTA GIORNI", "main_sub": "VENETIAN DIALECT FOR “40 DAYS”",
            "en_lines": ["Great catch, Hana! Quarantine actually comes from", "the Venetian phrase quaranta giorni, meaning forty days,", "rooted in the Latin word quadraginta for forty!"],
            "vi_lines": ["Tinh ý lắm Hana! “Quarantine” bắt nguồn từ cụm từ phương ngữ Venice", "“quaranta giorni” nghĩa là 40 ngày, gốc Latin “quadraginta” là 40!"],
            "wav": f"{ASSETS_DIR}/q_02_bella.wav", "ss": 0.0, "dur": None,
            "vid": _pick_vid("quarantine_v2_s02_talk_9x16-001.mp4", "quarantine_v2_s02_video-001.mp4"),
            "talk_win": None,
        },
        {
            "id": "s03a", "lip_sync": False, "y_shift": 0, "use_painted_main": False,
            "main_word": "1377 • TRENTINA", "main_sub": "RAGUSA PORT: 30-DAY ISOLATION",
            "en_lines": ["During the fourteenth-century Black Death, Ragusa", "first isolated incoming ships for thirty days."],
            "vi_lines": ["Trong đại dịch Cái Chết Đen thế kỷ 14, cảng Ragusa", "buộc tàu thuyền phải cách ly ngoài đảo trong 30 ngày."],
            "wav": f"{ASSETS_DIR}/q_03_bella.wav", "ss": 0.0, "dur": 6.00, "vid": f"{ASSETS_DIR}/quarantine_v2_s03_video-001.mp4",
        },
        {
            "id": "s03b", "lip_sync": False, "y_shift": 0, "use_painted_main": False,
            "main_word": "1448 • QUARANTINA", "main_sub": "VENICE EXTENDS IT TO 40 DAYS",
            "en_lines": ["Then in fourteen forty-eight, Venice extended it", "to forty days, creating the quarantina!"],
            "vi_lines": ["Đến năm 1448, Thượng viện Venice nâng thời gian cách ly", "lên 40 ngày, tạo ra thuật ngữ “quarantina”!"],
            "wav": f"{ASSETS_DIR}/q_03_bella.wav", "ss": 6.00, "dur": 5.83, "vid": f"{ASSETS_DIR}/quarantine_v2_s04_video-001.mp4",
        },
        {
            "id": "s04", "lip_sync": True, "y_shift": 0, "use_painted_main": False,
            "main_word": "QUARANTINE = 40 DAYS", "main_sub": "VENICE’S 1448 MARITIME RULE",
            "en_lines": ["So whenever we say quarantine, we are literally", "talking about Venice’s forty-day maritime rule", "to stop the plague!"],
            "vi_lines": ["Vậy là mỗi khi nói “quarantine”, ta đang nhắc tới quy tắc cách ly", "40 ngày trên biển của Venice để chặn dịch hạch!"],
            "wav": f"{ASSETS_DIR}/q_04_hana.wav", "ss": 0.0, "dur": 6.65,
            "vid": _pick_vid("quarantine_v2_s04_talk_9x16-001.mp4", "quarantine_v2_s04_talk_video-001.mp4"),
            "talk_win": None,
        },
    ]


def get_dur(path: str) -> float:
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path], text=True)
    return float(out.strip())


def build_cover_01s(out_mp4: str):
    im = Image.open(COVER_PAINTED).convert("RGBA").resize((1080, 1920), Image.Resampling.LANCZOS)
    d = ImageDraw.Draw(im)
    for y in range(115):
        d.line([(0, y), (1080, y)], fill=(7, 15, 32, int(140 * (1.0 - y / 115.0))))
    draw_top_header_and_logo(im)
    cov_png = os.path.join(BASE_DIR, "Cover_Quarantine_B2_V2_TOV.png")
    im.convert("RGB").save(cov_png, quality=95)
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", cov_png, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "0.1", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out_mp4], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def build_black_note_endcard(out_mp4: str):
    end_png = os.path.join(BASE_DIR, "tov_end_card.png")
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", end_png, "-ss", "7.28", "-i", f"{ASSETS_DIR}/q_04_hana.wav", "-filter_complex", "[0:v]fade=t=in:st=0:d=0.45,fps=30[v];[1:a]adelay=180|180,apad=whole_dur=3.1[a]", "-map", "[v]", "-map", "[a]", "-t", "3.1", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k", out_mp4], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def render_scene(sc: dict, out_mp4: str, work_dir: str):
    wav_dur = sc["dur"] if sc["dur"] else (get_dur(sc["wav"]) - sc["ss"])
    dur, vid_src = round(wav_dur + 0.35, 2), sc["vid"]
    if sc.get("lip_sync"):
        synced_vid = os.path.join(work_dir, f"lipsync_{sc['id']}.mp4")
        if not (os.path.exists(synced_vid) and os.path.getmtime(synced_vid) >= os.path.getmtime(sc["vid"])):
            info = build_lipsynced_scene_video(sc["vid"], sc["wav"], sc["ss"], wav_dur, dur, synced_vid, talk_win=sc.get("talk_win"))
            print(f"  [LipSync {sc['id']}] clauses={info['vo_clauses']} -> flow_segs={info['flow_segs']} speeds={info['speeds']}")
        vid_src = synced_vid
    base_ov = make_static_top_overlay(sc)
    all_words = [w for line in sc["en_lines"] for w in line.split()]
    n_words, ov_dir = len(all_words), os.path.join(work_dir, f"ov_{sc['id']}")
    os.makedirs(ov_dir, exist_ok=True)
    for idx in range(-1, n_words):
        draw_karaoke_eng_sub(base_ov, sc["en_lines"], idx).save(f"{ov_dir}/w_{idx+1:02d}.png")
    ys = sc["y_shift"]
    inputs = ["-stream_loop", "-1", "-i", vid_src, "-ss", str(sc["ss"]), "-t", str(wav_dur), "-i", sc["wav"]] + [a for idx in range(-1, n_words) for a in ("-i", f"{ov_dir}/w_{idx+1:02d}.png")]
    fc = [f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,delogo=x=842:y=1696:w=96:h=96,pad=1080:1920+{ys}:0:{ys}:color=#070f20,crop=1080:1920:0:0,fps=30[v0]"]
    w_step, prev = max(0.5, wav_dur - 0.15) / float(n_words), "v0"
    for k in range(n_words):
        t0, t1 = round(k * w_step, 3), (round((k + 1) * w_step, 3) if k < n_words - 1 else round(dur + 0.5, 3))
        fc.append(f"[{prev}][{k+3}:v]overlay=0:0:enable='between(t,{t0},{t1})'[vw{k}]")
        prev = f"vw{k}"
    fc.append(f"[1:a]adelay=80|80,apad=whole_dur={dur}[aout]")
    subprocess.run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", f"[{prev}]", "-map", "[aout]", "-t", str(dur), "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k", out_mp4], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    wdir = "/tmp/quarantine_v2_dialogue_build"
    os.makedirs(wdir, exist_ok=True)
    cov_mp4 = f"{wdir}/v2_00_cover.mp4"
    build_cover_01s(cov_mp4)
    parts = [cov_mp4]
    for sc in get_scenes():
        p = f"{wdir}/v2_{sc['id']}.mp4"
        render_scene(sc, p, wdir)
        parts.append(p)
    end_mp4 = f"{wdir}/v2_05_endcard.mp4"
    build_black_note_endcard(end_mp4)
    parts.append(end_mp4)
    inputs = [arg for p in parts for arg in ("-i", p)]
    streams = "".join(f"[{i}:v][{i}:a]" for i in range(len(parts)))
    final_mp4 = os.path.join(BASE_DIR, "WordOrigin_B2_Quarantine_V2_Karaoke_2D.mp4")
    subprocess.run([
        "ffmpeg", "-y", *inputs, "-filter_complex", f"{streams}concat=n={len(parts)}:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-profile:v", "main", "-level", "4.0", "-preset", "fast",
        "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k", final_mp4
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Built final Dialogue V2 video:", final_mp4)


if __name__ == "__main__":
    main()
