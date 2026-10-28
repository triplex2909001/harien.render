#!/usr/bin/env python3
"""Colab Remote Worker Payload (100% Pure OmniVoice Zero-Shot & Native Voice Design).
Supports per-item `instruct` (native OmniVoice Voice Design: gender, age, pitch, accent)
and `chain_ref_from` (zero-shot cloning from a newly designed voice in the same batch)
with ZERO artificial pitch-shift distortion!
Rule: File length <= 150 lines.
"""
import argparse, inspect, json, os, subprocess, sys, zipfile


def setup_colab_environment(task: str):
    if task == "render":
        subprocess.check_call(["apt-get", "update", "-qq"])
        subprocess.check_call(["apt-get", "install", "-y", "-qq", "ffmpeg"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "playwright"])
        subprocess.check_call(["npx", "-y", "playwright", "install-deps"])


def _extract_wav(audio):
    wav_data = audio[0] if isinstance(audio, (list, tuple)) else audio
    if hasattr(wav_data, "cpu"):
        wav_data = wav_data.cpu().numpy()
    if hasattr(wav_data, "squeeze"):
        wav_data = wav_data.squeeze()
    return wav_data


def _pad_ref_audio(ref_audio: str, tag: str = "default") -> str:
    import numpy as np
    import soundfile as sf
    data, sr = sf.read(ref_audio)
    if data.ndim > 1:
        data = data.mean(axis=1)
    nz = np.where(np.abs(data) > 0.003)[0]
    if len(nz) > 0:
        data = data[: min(len(data), int(nz[-1]) + int(0.12 * sr))]
    padded = np.concatenate([data, np.zeros(int(0.45 * sr), dtype=data.dtype)])
    out_ref = f"/tmp/ref_padded_{tag}.wav"
    sf.write(out_ref, padded, sr)
    return out_ref


def run_tts(text: str, out_path: str, ref_audio: str = None, ref_text: str = None, batch: list = None):
    import numpy as np
    import soundfile as sf
    import torch
    from omnivoice import OmniVoice

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    print(f"[Colab VM] Loading OmniVoice on {device} ({dtype})...")
    model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=device, dtype=dtype, load_asr=not bool(ref_text))
    sig_params = set(inspect.signature(model.generate).parameters.keys())

    base_kw = {}
    if ref_audio and os.path.exists(ref_audio):
        base_kw["ref_audio"] = _pad_ref_audio(ref_audio, "main")
        if ref_text:
            base_kw["ref_text"] = ref_text
    if "speed" in sig_params:
        base_kw["speed"] = 0.95

    generated_files = {}
    if batch:
        os.makedirs("/tmp/omni_batch", exist_ok=True)
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in batch:
                cid, ctext = item["id"], item["text"].strip()
                padded_text = ctext if ctext.endswith("?") else f"{ctext.rstrip('.!')}..."
                kw = dict(base_kw, text=padded_text)
                if item.get("instruct") and "instruct" in sig_params:
                    kw.pop("ref_audio", None)
                    kw.pop("ref_text", None)
                    kw["instruct"] = item["instruct"]
                elif item.get("chain_ref_from") and item["chain_ref_from"] in generated_files:
                    src_id = item["chain_ref_from"]
                    kw["ref_audio"] = _pad_ref_audio(generated_files[src_id]["path"], src_id)
                    kw["ref_text"] = generated_files[src_id]["text"]
                if item.get("speed") and "speed" in sig_params:
                    kw["speed"] = float(item["speed"])
                if item.get("lang") and "language" in sig_params:
                    kw["language"] = item["lang"]
                if item.get("seed") is not None:
                    torch.manual_seed(int(item["seed"]))
                    if torch.cuda.is_available():
                        torch.cuda.manual_seed_all(int(item["seed"]))
                wav_data = _extract_wav(model.generate(**kw)).astype(np.float32)
                fade_len = min(len(wav_data), int(0.15 * 24000))
                if fade_len > 0:
                    wav_data[-fade_len:] *= np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
                unpadded_p = f"/tmp/omni_batch/{cid}_clean.wav"
                sf.write(unpadded_p, wav_data, 24000)
                generated_files[cid] = {"path": unpadded_p, "text": ctext}
                wav_padded = np.concatenate([wav_data, np.zeros(24000, dtype=wav_data.dtype)])
                p = f"/tmp/omni_batch/{cid}.wav"
                sf.write(p, wav_padded, 24000)
                zf.write(p, arcname=f"{cid}.wav")
                print(f"[Colab VM] Synthesized [{cid}] ({len(wav_data)/24000:.2f}s + 1.0s silence): {ctext}")
        return

    kw = dict(base_kw, text=text if text.endswith("?") else f"{text.rstrip('.!')}...")
    wav_data = _extract_wav(model.generate(**kw))
    sf.write(out_path, np.concatenate([wav_data, np.zeros(24000, dtype=wav_data.dtype)]), 24000)


def main():
    parser = argparse.ArgumentParser(description="Colab Worker Payload")
    parser.add_argument("--task", choices=["tts", "render", "ffmpeg"], required=True)
    parser.add_argument("--payload", help="JSON string or file containing task parameters")
    args = parser.parse_args()
    setup_colab_environment(args.task)
    params = json.load(open(args.payload, encoding="utf-8")) if (args.payload and os.path.exists(args.payload)) else (json.loads(args.payload) if args.payload else {})
    if args.task == "tts":
        run_tts(params.get("text", ""), params.get("out", "output.wav"), params.get("ref_audio"), params.get("ref_text"), params.get("batch"))
    elif args.task == "ffmpeg" and params.get("cmd"):
        subprocess.check_call(params["cmd"])


if __name__ == "__main__":
    main()
