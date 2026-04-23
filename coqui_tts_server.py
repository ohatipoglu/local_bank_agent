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


def main():
    """Main entry point for subprocess call."""
    if len(sys.argv) < 3:
        print(
            "Usage: python coqui_tts_server.py <text> <output_file> [speaker_wav]",
            file=sys.stderr,
        )
        sys.exit(1)

    text_arg = sys.argv[1]
    
    if text_arg.startswith("FILE:"):
        file_path = text_arg[5:]
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
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
