#!/usr/bin/env python3
"""Monotonic Piecewise-Linear & Optical-Flow 2D Lip-Sync Engine (`word_origin_lipsync.py`).
Follows `studio/pipelines/lipsync_flow_single.py` & `lipsync_flow_retime.py`:
- OmniVoice WAV is the 1.0x master track (shifted by +0.08s to match scene audio delay).
- Matches OmniVoice clauses (`o_segs`) to Flow video speech segments (`f_segs`) via optimal
  adjacent-clause grouping so every clause speed lies in `[0.65x, 1.35x]` and pauses stay shut.
- Uses slope-1 lead-in/tail extrapolation and Farneback optical flow (`_interp_flow`).
Rule: File length <= 150 lines (AGENTS.md).
"""
from itertools import combinations
import os, subprocess, tempfile, wave
import cv2
import numpy as np


def _load_rms_db(media_path: str, ss: float = 0.0, dur: float = None, sr: int = 24000) -> tuple:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_w = tmp.name
    try:
        cmd = ["ffmpeg", "-y", *(("-ss", str(ss)) if ss > 0 else ()), *(("-t", str(dur)) if dur else ()), "-i", media_path, "-vn", "-ac", "1", "-ar", str(sr), tmp_w]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with wave.open(tmp_w, "rb") as wf:
            pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        win, hop = int(0.025 * sr), int(0.010 * sr)
        rms = np.sqrt([np.mean(pcm[i * hop : i * hop + win] ** 2) + 1e-12 for i in range(max(1, (len(pcm) - win) // hop + 1))])
        return 20.0 * np.log10(rms), len(pcm) / float(sr)
    finally:
        if os.path.exists(tmp_w):
            os.remove(tmp_w)


def _split_voiced(voiced: np.ndarray, gap_sec: float, min_dur: float = 0.14) -> list:
    if len(voiced) == 0:
        return []
    cuts = np.where(np.diff(voiced) * 0.01 >= gap_sec)[0]
    starts = np.r_[voiced[0], voiced[cuts + 1]]
    ends = np.r_[voiced[cuts], voiced[-1]] + 1
    return [(round(float(a) * 0.01, 2), round(float(b) * 0.01, 2))
            for a, b in zip(starts, ends) if (b - a) * 0.01 >= min_dur]


def _group_clauses(segs: list, k: int) -> list:
    if k <= 1 or len(segs) <= 1:
        return [[(segs[0][0], segs[-1][1])]]
    if k == len(segs):
        return [segs]
    out = []
    for splits in combinations(range(1, len(segs)), k - 1):
        idx = (0,) + splits + (len(segs),)
        out.append([(segs[idx[i]][0], segs[idx[i + 1] - 1][1]) for i in range(k)])
    return out


def match_omni_and_flow_clauses(
    wav_path: str, ss: float, wav_dur: float, clip_path: str, src_dur: float, rel_db: float = 16.0
) -> tuple:
    """Find optimal (o_segs, f_segs) grouping with max clause count where all speeds in [0.65, 1.35]."""
    o_db, _ = _load_rms_db(wav_path, ss=ss, dur=wav_dur)
    o_voiced = np.where(o_db > o_db.max() - 28.0)[0]
    max_flow_s = min(src_dur - 0.15, wav_dur + 1.45)
    f_db, _ = _load_rms_db(clip_path, dur=max_flow_s)
    f_voiced = np.where(f_db > f_db.max() - rel_db)[0]

    best, best_score = None, (0, -999.0)
    for o_rel, o_gap in ((28.0, 0.18), (22.0, 0.08)):
        o_base = _split_voiced(np.where(o_db > o_db.max() - o_rel)[0], o_gap, min_dur=0.12)
        for f_gap in (0.25, 0.30, 0.20, 0.35):
            f_segs = _split_voiced(f_voiced, f_gap, min_dur=0.18)
            if not f_segs or len(f_segs) > len(o_base):
                continue
            for o_cand in _group_clauses(o_base, len(f_segs)):
                speeds = [(fb - fa) / max(0.1, ob - oa) for (oa, ob), (fa, fb) in zip(o_cand, f_segs)]
                if all(0.65 <= s <= 1.35 for s in speeds):
                    sc = (len(f_segs), -sum(abs(s - 1.0) for s in speeds))
                    if sc > best_score:
                        best, best_score = (o_cand, f_segs), sc
    if best:
        return best
    f_fb = _split_voiced(f_voiced, 0.25, min_dur=0.18) or [(0.25, round(max_flow_s - 0.2, 2))]
    o_fb = o_base or [(0.15, round(max(0.5, wav_dur - 0.15), 2))]
    return [(o_fb[0][0], o_fb[-1][1])], [(f_fb[0][0], f_fb[-1][1])]


def _interp_flow(f0: np.ndarray, f1: np.ndarray, a: float, small: tuple = (270, 480)) -> np.ndarray:
    if a <= 0.02:
        return f0
    if a >= 0.98:
        return f1
    h, w = f0.shape[:2]
    g0 = cv2.cvtColor(cv2.resize(f0, small), cv2.COLOR_BGR2GRAY)
    g1 = cv2.cvtColor(cv2.resize(f1, small), cv2.COLOR_BGR2GRAY)
    fl = cv2.calcOpticalFlowFarneback(g0, g1, None, 0.5, 3, 21, 3, 5, 1.2, 0)
    fl = cv2.resize(fl, (w, h)) * (w / float(small[0]))
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    w0 = cv2.remap(f0, gx - a * fl[..., 0], gy - a * fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    w1 = cv2.remap(f1, gx + (1.0 - a) * fl[..., 0], gy + (1.0 - a) * fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return cv2.addWeighted(w0, 1.0 - a, w1, a, 0)


def _build_monotonic_anchors(o_segs: list, f_segs: list, total_dur: float, src_dur: float, audio_delay: float = 0.08, pad: float = 0.04) -> tuple:
    ot = [max(0.02, t + audio_delay) for (a, b) in o_segs for t in (a - pad, b + pad)]
    ft = [float(np.clip(t, 0.02, src_dur - 0.06)) for (a, b) in f_segs for t in (a - pad, b + pad)]
    xs = [0.0] + ot + [total_dur]
    ys = [max(0.0, ft[0] - ot[0])] + ft + [min(src_dur - 0.04, ft[-1] + max(0.10, total_dur - ot[-1]))]
    for i in range(1, len(xs)):
        if xs[i] <= xs[i - 1]:
            xs[i] = xs[i - 1] + 0.02
        if ys[i] < ys[i - 1]:
            ys[i] = ys[i - 1]
    speeds = [round((ft[i + 1] - ft[i]) / max(0.05, ot[i + 1] - ot[i]), 2) for i in range(0, len(ot), 2)]
    return np.array(xs, dtype=np.float64), np.array(ys, dtype=np.float64), speeds


def build_lipsynced_scene_video(
    raw_mp4: str, wav_path: str, ss: float, wav_dur: float, total_dur: float,
    out_mp4: str, talk_win: tuple = None, fps: int = 30
) -> dict:
    """Piecewise-warp ONE continuous Flow clip onto OmniVoice clauses with Farneback optical flow."""
    cap = cv2.VideoCapture(raw_mp4)
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frames = []
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        frames.append(fr)
    cap.release()
    src_dur = len(frames) / float(src_fps)
    o_segs, f_segs = (talk_win if (talk_win and isinstance(talk_win[0], list))
                      else match_omni_and_flow_clauses(wav_path, ss, wav_dur, raw_mp4, src_dur))
    if talk_win and not isinstance(talk_win[0], list):
        f_segs, o_segs = [talk_win], [(o_segs[0][0], o_segs[-1][1])]
    xs, ys, speeds = _build_monotonic_anchors(o_segs, f_segs, total_dur, src_dur)
    h, w = frames[0].shape[:2]
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
         "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", out_mp4],
        stdin=subprocess.PIPE
    )
    last_pos = len(frames) - 1.001
    for k in range(int(round(total_dur * fps))):
        pos = float(np.clip(float(np.interp(k / float(fps), xs, ys)) * src_fps, 0.0, last_pos))
        idx = int(pos)
        proc.stdin.write(_interp_flow(frames[idx], frames[min(idx + 1, len(frames) - 1)], pos - idx).tobytes())
    proc.stdin.close()
    proc.wait()
    return {"vo_clauses": o_segs, "flow_segs": f_segs, "speeds": speeds, "talk_win": (f_segs[0][0], f_segs[-1][1])}
