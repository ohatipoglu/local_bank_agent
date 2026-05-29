"""
Coqui XTTS v2 TTS Server Script

This script is called as a subprocess from the main application.
It uses Coqui XTTS v2 to synthesize speech from text.

Usage:
    python coqui_tts_server.py <text> <output_file> [speaker_wav]
    
    If <text> starts with "FILE:", it is treated as a file path containing the text.

Args:
    text: Text to synthesize, or "FILE:path/to/file.txt" to read from a file.
    output_file: Output WAV file path
    speaker_wav: (Optional) Reference audio file for voice cloning

Requires:
    - conda environment: coqui_env
    - packages: TTS
"""

import os
import sys

# Force UTF-8 encoding for standard streams on Windows to prevent UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import warnings

import torch

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")


def synthesize(text: str, output_file: str, speaker_wav: str = None):
    """
    Synthesize speech using Coqui XTTS v2.

    Args:
        text: Text to synthesize
        output_file: Output WAV file path
        speaker_wav: Reference audio for voice cloning (optional)
    """
    from TTS.api import TTS

    # Determine device
    use_gpu = torch.cuda.is_available()
    device = "cuda" if use_gpu else "cpu"

    print(f"Loading XTTS v2 model on {device}...", file=sys.stderr)

    # Initialize TTS
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2").to(device)

    # Synthesize
    print(f"Synthesizing text: {text[:50]}...", file=sys.stderr)

    # Use default speaker if no reference provided
    if speaker_wav and os.path.exists(speaker_wav):
        tts.tts_to_file(
            text=text, file_path=output_file, speaker_wav=speaker_wav, language="tr"
        )
    else:
        # Fallback to the first available built-in speaker
        if hasattr(tts, "speakers") and tts.speakers and len(tts.speakers) > 0:
            speaker_name = tts.speakers[0]
            print(f"No speaker_wav provided, using default speaker: {speaker_name}", file=sys.stderr)
            tts.tts_to_file(text=text, file_path=output_file, speaker=speaker_name, language="tr")
        else:
            print("Error: No speaker_wav provided and no built-in speakers found.", file=sys.stderr)
            return False

    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file)
        print(
            f"Successfully generated: {output_file} ({file_size/1024:.1f} KB)",
            file=sys.stderr,
        )
        return True
    else:
        print("Failed to generate output file", file=sys.stderr)
        return False


def run_server(host="127.0.0.1", port=8001):
    """Run persistent Flask server for Coqui XTTS v2 synthesis."""
    from flask import Flask, request, Response, jsonify
    from TTS.api import TTS
    import tempfile
    import os

    app = Flask(__name__)

    # Determine device
    use_gpu = torch.cuda.is_available()
    device = "cuda" if use_gpu else "cpu"

    print(f"Loading XTTS v2 model on {device} (Flask Server)...", file=sys.stderr)
    try:
        tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        print("XTTS v2 model loaded successfully. Server starting...", file=sys.stderr)
    except Exception as e:
        print(f"Failed to load XTTS v2 model: {e}", file=sys.stderr)
        sys.exit(1)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ready", "device": device})

    @app.route("/synthesize", methods=["POST"])
    def synthesize_endpoint():
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid JSON"}), 400

            text = data.get("text", "").strip()
            speaker_wav = data.get("speaker_wav")

            if not text:
                return jsonify({"error": "Empty text provided"}), 400

            # Create temporary WAV output file
            temp_fd, temp_path = tempfile.mkstemp(suffix=".wav")
            os.close(temp_fd)

            try:
                if speaker_wav and os.path.exists(speaker_wav):
                    tts.tts_to_file(
                        text=text,
                        file_path=temp_path,
                        speaker_wav=speaker_wav,
                        language="tr"
                    )
                else:
                    if hasattr(tts, "speakers") and tts.speakers and len(tts.speakers) > 0:
                        speaker_name = tts.speakers[0]
                        tts.tts_to_file(
                            text=text,
                            file_path=temp_path,
                            speaker=speaker_name,
                            language="tr"
                        )
                    else:
                        return jsonify({"error": "No speaker_wav provided and no default speaker found"}), 400

                if os.path.exists(temp_path):
                    with open(temp_path, "rb") as f:
                        wav_bytes = f.read()
                    return Response(wav_bytes, mimetype="audio/wav")
                else:
                    return jsonify({"error": "Failed to generate output file"}), 500

            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass

        except Exception as err:
            return jsonify({"error": str(err)}), 500

    app.run(host=host, port=port, debug=False, threaded=True)


def main():
    """Main entry point for CLI or server."""
    if "--server" in sys.argv:
        host = "127.0.0.1"
        port = 8001

        # Parse potential --host and --port arguments
        for i, arg in enumerate(sys.argv):
            if arg == "--host" and i + 1 < len(sys.argv):
                host = sys.argv[i + 1]
            elif arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])

        run_server(host, port)
        sys.exit(0)

    # Original CLI logic
    if len(sys.argv) < 3:
        print(
            "Usage: python coqui_tts_server.py <text> <output_file> [speaker_wav] or python coqui_tts_server.py --server [--host <host>] [--port <port>]",
            file=sys.stderr,
        )
        sys.exit(1)

    text_arg = sys.argv[1]

    if text_arg.startswith("FILE:"):
        file_path = text_arg[5:]
        if os.path.exists(file_path):
            with open(file_path, encoding="utf-8") as f:
                text = f.read().strip()
        else:
            print(f"Error: Text file not found: {file_path}", file=sys.stderr)
            sys.exit(1)
    else:
        text = text_arg

    output_file = sys.argv[2]
    speaker_wav = sys.argv[3] if len(sys.argv) > 3 else None

    if not text:
        print("Error: Empty text provided.", file=sys.stderr)
        sys.exit(1)

    try:
        success = synthesize(text, output_file, speaker_wav)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
