#!/usr/bin/env python3
"""HanaRio English GHA Engine Helper (100% OmniVoice + HTML5 Templates T01-T08 + Live 3D Mascot Cover).
- Zero edge-tts / gTTS. Uses pre-synthesized Colab OmniVoice zero-shot cloned clips.
- Renders authentic T01-T08 HTML5 templates + transparent Cover UI Overlay + Live Flow Mascot Cover.
Rule: File length <= 150 lines (AGENTS.md).
"""
import glob, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def install_bundled_fonts():
    fdir = os.path.expanduser("~/.local/share/fonts/hanario")
    os.makedirs(fdir, exist_ok=True)
    for f in glob.glob("assets/fonts/*.ttf"):
        shutil.copy2(f, os.path.join(fdir, os.path.basename(f)))
    if shutil.which("fc-cache"):
        subprocess.run(["fc-cache", "-f", fdir], capture_output=True)

def get_template_cfg(ep_id: str, level: str = "B1") -> dict:
    os.environ["NO_COLAB"] = "1"
    from scripts import tts_10words_builder_gha; sys.modules["scripts.tts_10words_builder"] = tts_10words_builder_gha
    from scripts import render_t05_grammar_gha; sys.modules["scripts.render_t05_grammar"] = render_t05_grammar_gha
    m = re.match(r"^(T0[1-8])_EP0*(\d+)", ep_id.upper())
    t, ep_num = (m.group(1) if m else "T01"), (int(m.group(2)) if m else 3)
    idx = max(0, min(2, ep_num - 1))
    lvl = (level or ep_id.split("_")[-1] or "B1").upper()
    lm = "Monolingual" if any(k in lvl for k in ("B2", "C1", "C2", "IELTS")) else "Bilingual"
    from scripts.episodes_data_t01_t03 import T01_EPISODES, T02_EPISODES, T03_EPISODES
    from scripts.episodes_data_t04_t05 import T04_EPISODES, T05_EPISODES
    ep_map = {"T01": T01_EPISODES, "T02": T02_EPISODES, "T03": T03_EPISODES, "T04": T04_EPISODES, "T05": T05_EPISODES}
    if t in ep_map:
        ep = dict(ep_map[t][idx])
        m_id = ep.get("mascot_id", "rio" if t in ("T02", "T03", "T04") else "thuy_duong")
        cov_id = ep.get("hook_cov_id") or (ep.get("pattern", {}).get("cov_id")) or f"line1_cov_{t.lower()}_ep{ep_num:03d}"
        hw = ep.get("hook_wav") or f"assets/voice_samples/{m_id}_clips/{cov_id}.wav"
        flow = ep["flow_raw_mp4"] if os.path.exists(ep["flow_raw_mp4"]) else ep_map[t][0]["flow_raw_mp4"]
        overrides = {
            ("T01", 3): ("thuy_duong", "studio/outputs/01_presenter_covers/clauses/t01_ep003_b1_full.mp4", "assets/voice_samples/thuy_duong_clips/line1_cov_t01_ep003.wav"),
            ("T02", 3): ("hana", "studio/outputs/01_presenter_covers/clauses/t02_ep003_b1_full.mp4", "assets/voice_samples/hana_clips/line1_cov_t02_ep001_b1.wav"),
            ("T03", 3): ("rio", "studio/outputs/01_presenter_covers/clauses/t03_ep003_b1_full.mp4", "assets/voice_samples/rio_clips/line1_cov_t03_ep003_2c.wav"),
            ("T04", 3): ("thuy_duong", "studio/outputs/01_presenter_covers/clauses/t04_ep003_b1_full.mp4", "assets/voice_samples/thuy_duong_clips/t04_cov_i_think_sv.wav"),
            ("T05", 3): ("thuy_duong", "studio/outputs/01_presenter_covers/clauses/t05_ep003_b1_full.mp4", "assets/voice_samples/thuy_duong_clips/t05_cover_v2.wav"),
        }
        if (t, ep_num) in overrides:
            om, oflow, ohw = overrides[(t, ep_num)]
            ep["mascot_id"] = om
            if os.path.exists(oflow): flow = oflow
            if os.path.exists(ohw): hw = ohw
        return {"t_prefix": t, "ep_num": ep_num, "idx": idx, "level": lvl, "lang_mode": lm, "ep": ep, "flow_mp4": flow, "hook_wav": hw}
    hw_map = {
        "T06": (f"assets/voice_samples/hana_clips/line1_cov_t06_ep{ep_num:03d}.wav", "assets/voice_samples/hana_clips/t06_cover_vi.wav", "studio/outputs/01_presenter_covers/clauses/t06_ep003_b1_full.mp4"),
        "T07": (f"assets/voice_samples/hana_clips/line1_cov_t07_ep{ep_num:03d}.wav", "assets/voice_samples/hana_clips/t07_cover_vi.wav", "studio/outputs/01_presenter_covers/clauses/t07_ep003_b1_full.mp4"),
        "T08": ("assets/voice_samples/thuy_duong_clips/t08_cover_vi.wav", "assets/voice_samples/thuy_duong_clips/t08_cover_vi.wav", "studio/outputs/01_presenter_covers/clauses/t08_ep003_b1_full.mp4"),
    }
    hw1, hw2, flow = hw_map[t]
    return {"t_prefix": t, "ep_num": ep_num, "idx": idx, "level": lvl, "lang_mode": lm, "ep": {"ep_code": f"EP{ep_num:03d}"}, "flow_mp4": flow, "hook_wav": hw1 if os.path.exists(hw1) else hw2}


def build_omni_voice_files(ep_id: str, vdir: str, level: str = "B1") -> list:
    if ep_id.upper().startswith("POST_"):
        from scripts.word_origin_gha_engine import run_omnivoice_word_origin; return run_omnivoice_word_origin(ep_id, os.path.dirname(vdir), level)
    os.makedirs(vdir, exist_ok=True); cfg = get_template_cfg(ep_id, level)
    t, ep, lm = cfg["t_prefix"], cfg["ep"], cfg["lang_mode"]
    hook_dst, vo_dst, st_dst = os.path.join(vdir, "hook.wav"), os.path.join(vdir, "vo.wav"), os.path.join(vdir, "st.wav")
    shutil.copy2(cfg["hook_wav"], hook_dst)
    if t == "T01":
        from scripts.tts_10words_builder_gha import build_10words_voice_wav
        from scripts.render_10words_bilingual import build_10words_soundtrack
        build_10words_voice_wav(vo_dst, words=ep["words"], cover_s=0.0, en_tempo=0.80, char_key=ep.get("mascot_id", "thuy_duong"))
        build_10words_soundtrack(st_dst, num_words=len(ep["words"]), cover_s=0.0)
    elif t == "T02":
        from scripts.t02_confusing_data import build_t02_voice_and_schedule
        from scripts.render_t02_confusing import build_t02_soundtrack
        _, tot, cov_s, intro_s, sched, _ = build_t02_voice_and_schedule(vo_dst, ep["pairs"], en_tempo=0.80, skip_cover=True, char_key=ep.get("mascot_id", "rio"))
        build_t02_soundtrack(st_dst, tot, cov_s, intro_s, sched)
    elif t == "T03":
        from scripts.t03_upgrade_data import build_t03_voice_and_schedule
        from scripts.render_t03_upgrade import build_t03_soundtrack
        _, tot, cov_s, intro_s, sched, _ = build_t03_voice_and_schedule(vo_dst, ep["items"], en_tempo=0.80, skip_cover=True)
        build_t03_soundtrack(st_dst, tot, cov_s, intro_s, sched)
    elif t == "T04":
        from scripts.t04_patterns_data import build_t04_slide_voice
        vo_info = build_t04_slide_voice(vo_dst, ep["pattern"], ep_num=cfg["ep_num"], skip_cover=True)
        shutil.copy2(vo_info["outro_wav"], os.path.join(vdir, "outro.wav"))
        return ["hook.wav", "vo.wav", "outro.wav"]
    elif t == "T05":
        from scripts.t05_grammar_data import GRAMMAR_TRAPS_DB, build_t05_voice_and_schedule
        from scripts.render_t05_grammar_gha import build_t05_soundtrack
        _, tot, cov_s, sched, _ = build_t05_voice_and_schedule(vo_dst, ep.get("traps") or GRAMMAR_TRAPS_DB[:3], en_tempo=0.80, skip_cover=True, lang_mode=lm)
        build_t05_soundtrack(st_dst, tot, cov_s, sched)
    elif t == "T06":
        from scripts.t06_phrasal_data import PHRASAL_VERBS_DB, build_t06_voice_and_schedule
        from scripts.render_t06_phrasal import build_t06_soundtrack
        _, tot, cov_s, sched, _ = build_t06_voice_and_schedule(vo_dst, PHRASAL_VERBS_DB[:5], en_tempo=0.82, skip_cover=True)
        build_t06_soundtrack(st_dst, tot, cov_s, sched)
    elif t == "T07":
        from scripts.t07_idioms_data import DAILY_IDIOMS_DB, build_t07_voice_and_schedule
        from scripts.render_t07_idioms import build_t07_soundtrack
        _, tot, cov_s, sched, _ = build_t07_voice_and_schedule(vo_dst, DAILY_IDIOMS_DB[:3], en_tempo=0.82, skip_cover=True)
        build_t07_soundtrack(st_dst, tot, cov_s, sched)
    else:
        from scripts.t08_listening_data import LISTENING_DB, build_t08_voice_and_schedule
        from scripts.render_t08_listening import build_t08_soundtrack
        _, tot, cov_s, sched, _ = build_t08_voice_and_schedule(vo_dst, LISTENING_DB[:3], lang_mode=lm, skip_cover=True)
        build_t08_soundtrack(st_dst, tot, cov_s, sched)
    return ["hook.wav", "vo.wav", "st.wav"]


def render_template_body_and_cover_ui(ep_id: str, wdir: str, level: str = "B1") -> dict:
    if ep_id.upper().startswith("POST_"):
        from scripts.word_origin_gha_engine import run_hyperframes_word_origin; return run_hyperframes_word_origin(ep_id, wdir, level)
    install_bundled_fonts(); cfg = get_template_cfg(ep_id, level)
    t, ep, lm = cfg["t_prefix"], cfg["ep"], cfg["lang_mode"]
    fdir, cdir = os.path.join(wdir, "frames"), os.path.join(wdir, "cover_flow")
    os.makedirs(fdir, exist_ok=True); os.makedirs(cdir, exist_ok=True); os.makedirs("output", exist_ok=True)
    body_mp4, ui_png, flow_dst = os.path.join(wdir, "body_raw.mp4"), os.path.join(fdir, "ui_overlay.png"), os.path.join(cdir, "flow_raw.mp4")
    shutil.copy2(cfg["flow_mp4"], flow_dst)
    from scripts.render_english_video import find_browser
    from studio.pipelines.line1_presenter_compositor import render_transparent_ui_overlay
    if t == "T01":
        from scripts.render_10words_bilingual import build_t01_cover_html, render_10words_video
        render_10words_video(body_mp4, ep_cfg=ep, skip_cover=True); cov_html = build_t01_cover_html(ep)
    elif t == "T02":
        from scripts.render_t02_confusing import build_t02_cover_html, render_t02_confusing
        render_t02_confusing(body_mp4, ep_cfg=ep, skip_cover=True); cov_html = build_t02_cover_html(ep)
    elif t == "T03":
        from scripts.render_t03_upgrade import build_t03_cover_html, render_t03_upgrade
        render_t03_upgrade(body_mp4, ep_cfg=ep, skip_cover=True); cov_html = build_t03_cover_html(ep)
    elif t == "T04":
        from scripts.run_t04_movie_edition import render_t04_episode
        from scripts.render_t04_patterns import build_t04_frame_html
        render_t04_episode(body_mp4, ep_cfg=ep, skip_cover=True); cov_html = build_t04_frame_html("cover", ep["pattern"], ep_num=cfg["ep_num"], ep_cfg=ep)
    elif t == "T05":
        from scripts.render_t05_grammar_gha import render_t05_grammar
        from scripts.t05_grammar_html import build_t05_cover_html
        render_t05_grammar(body_mp4, ep_cfg=ep, skip_cover=True, lang_mode=lm); cov_html = build_t05_cover_html(ep, lang_mode=lm)
    elif t == "T06":
        from scripts.render_t06_phrasal import build_t06_frame_html, render_t06_phrasal
        from scripts.t06_phrasal_data import PHRASAL_VERBS_DB
        render_t06_phrasal(body_mp4, skip_cover=True); cov_html = build_t06_frame_html("cover", 0, PHRASAL_VERBS_DB[0], PHRASAL_VERBS_DB[:5])
    elif t == "T07":
        from scripts.render_t07_idioms import build_t07_frame_html, render_t07_idioms
        from scripts.t07_idioms_data import DAILY_IDIOMS_DB
        render_t07_idioms(body_mp4, skip_cover=True); cov_html = build_t07_frame_html("cover", 0, DAILY_IDIOMS_DB[0], 5)
    else:
        from scripts.render_t08_listening import build_t08_frame_html, render_t08_listening
        from scripts.t08_listening_data import LISTENING_DB
        render_t08_listening(body_mp4, lang_mode=lm, skip_cover=True); cov_html = build_t08_frame_html("cover", 0, LISTENING_DB[0], lang_mode=lm)
    render_transparent_ui_overlay(cov_html, find_browser(), ui_png)
    return {"body_raw": body_mp4, "ui_overlay": ui_png, "flow_raw": flow_dst}
