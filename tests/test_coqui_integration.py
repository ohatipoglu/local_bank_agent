"""
Coqui TTS Integration Test Script

This script tests the Coqui XTTS v2 integration with the Local Bank AI Agent.
It validates:
1. Conda environment (coqui_env) exists
2. TTS package is installed in coqui_env
3. Reference voice file exists
4. Coqui server script is available
5. End-to-end TTS synthesis works

Usage:
    python test_coqui_integration.py
"""
import os
import sys
import subprocess
import time
from pathlib import Path


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_conda_env():
    """Check if coqui_env conda environment exists."""
    print_section("1. Checking Conda Environment")
    
    try:
        # Try different conda commands for Windows
        conda_cmds = [
            ["conda", "env", "list"],
            ["C:\\Users\\HOME\\anaconda3\\Scripts\\conda.exe", "env", "list"],
        ]
        
        for conda_cmd in conda_cmds:
            try:
                result = subprocess.run(
                    conda_cmd,
                    capture_output=True, text=True, timeout=10,
                    shell=True
                )
                
                if result.returncode == 0 and "coqui_env" in result.stdout:
                    print("✅ coqui_env found")
                    return True
                elif result.returncode == 0:
                    print("❌ coqui_env not found")
                    print("\nAvailable environments:")
                    print(result.stdout)
                    return False
            except (FileNotFoundError, OSError):
                continue
        
        print("❌ Could not find conda executable")
        return False
    except Exception as e:
        print(f"❌ Error checking conda environments: {e}")
        return False


def check_tts_installed():
    """Check if TTS package is installed in coqui_env."""
    print_section("2. Checking TTS Package Installation")
    
    try:
        cmd = 'conda run -n coqui_env python -c "from TTS.api import TTS; print(\'TTS installed\')"'
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=30,
            shell=True
        )
        
        if result.returncode == 0:
            print("✅ TTS package is installed in coqui_env")
            print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print("❌ TTS package not found in coqui_env")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"❌ Error checking TTS installation: {e}")
        return False


def check_reference_audio():
    """Check if reference audio files exist."""
    print_section("3. Checking Reference Audio Files")
    
    project_root = Path(__file__).parent
    reference_wav = project_root / "referans_ses.wav"
    models_wav = project_root / "models" / "coqui_reference.wav"
    
    all_good = True
    
    # Check original reference
    if reference_wav.exists():
        file_size = reference_wav.stat().st_size
        print(f"✅ referans_ses.wav found ({file_size/1024:.1f} KB)")
    else:
        print("❌ referans_ses.wav not found")
        all_good = False
    
    # Check models directory copy
    if models_wav.exists():
        file_size = models_wav.stat().st_size
        print(f"✅ models/coqui_reference.wav found ({file_size/1024:.1f} KB)")
    else:
        print("⚠️  models/coqui_reference.wav not found")
        print("   (Will use referans_ses.wav directly)")
    
    return all_good


def check_server_script():
    """Check if Coqui server script exists."""
    print_section("4. Checking Server Script")
    
    project_root = Path(__file__).parent
    server_script = project_root / "coqui_tts_server.py"
    config_file = project_root / "coqui_tts_config.json"
    
    all_good = True
    
    if server_script.exists():
        print(f"✅ coqui_tts_server.py found")
    else:
        print("❌ coqui_tts_server.py not found")
        all_good = False
    
    if config_file.exists():
        print(f"✅ coqui_tts_config.json found")
        # Show config contents
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"   Config: {json.dumps(config, indent=2)}")
    else:
        print("⚠️  coqui_tts_config.json not found (will use defaults)")
    
    return all_good


def test_tts_synthesis():
    """Test end-to-end TTS synthesis."""
    print_section("5. Testing TTS Synthesis")
    
    project_root = Path(__file__).parent
    server_script = project_root / "coqui_tts_server.py"
    reference_wav = project_root / "referans_ses.wav"
    output_file = project_root / "test_coqui_output.wav"
    
    if not server_script.exists():
        print("❌ Server script not found, skipping synthesis test")
        return False
    
    if not reference_wav.exists():
        print("❌ Reference audio not found, skipping synthesis test")
        return False
    
    test_text = "Merhaba, bu bir test konuşmasıdır. Coqui TTS entegrasyonu başarılı."
    
    print(f"Test text: {test_text}")
    print(f"Reference: {reference_wav}")
    print(f"Output: {output_file}")
    print("\n⏳ Synthesizing (this may take 10-30 seconds)...")
    
    try:
        start_time = time.time()
        
        # Use shell=True for Windows conda compatibility
        cmd = f'conda run -n coqui_env python "{server_script}" "{test_text}" "{output_file}" "{reference_wav}"'
        
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=120,
            cwd=str(project_root),
            shell=True
        )
        
        elapsed = time.time() - start_time
        
        # Log stderr
        if result.stderr:
            for line in result.stderr.strip().split('\n')[-5:]:  # Last 5 lines
                if line.strip():
                    print(f"   {line.strip()}")
        
        if result.returncode == 0 and output_file.exists():
            file_size = output_file.stat().st_size
            print(f"\n✅ Synthesis successful!")
            print(f"   Time: {elapsed:.2f}s")
            print(f"   File size: {file_size/1024:.1f} KB")
            print(f"   Output: {output_file}")
            
            # Cleanup test file
            try:
                output_file.unlink()
                print(f"   (Test file cleaned up)")
            except:
                pass
            
            return True
        else:
            print(f"\n❌ Synthesis failed (exit code {result.returncode})")
            if result.stderr:
                print(f"   Error: {result.stderr[-500:]}")  # Last 500 chars
            return False
            
    except subprocess.TimeoutExpired:
        print(f"\n❌ Synthesis timed out (>120s)")
        return False
    except Exception as e:
        print(f"\n❌ Error during synthesis: {e}")
        return False


def print_summary(results):
    """Print test summary."""
    print_section("Test Summary")
    
    checks = [
        ("Conda Environment", results[0]),
        ("TTS Package", results[1]),
        ("Reference Audio", results[2]),
        ("Server Script", results[3]),
        ("TTS Synthesis", results[4]),
    ]
    
    for name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {name}")
    
    all_passed = all(results)
    print("\n" + "=" * 60)
    if all_passed:
        print("  ✅ All tests passed! Coqui TTS is ready to use.")
        print("\nNext steps:")
        print("  1. Start the web server: python web_server.py")
        print("  2. Open browser: http://localhost:8000")
        print("  3. Select 'Coqui XTTS' as TTS engine")
        print("  4. Test voice synthesis")
    else:
        print("  ⚠️  Some tests failed. Please review the errors above.")
        print("\nTroubleshooting:")
        print("  - Ensure coqui_env exists: conda env list")
        print("  - Install TTS: conda activate coqui_env && pip install TTS>=0.20.0")
        print("  - Check reference audio: referans_ses.wav")
        print("  - See COQUI_INSTALL_GUIDE.md for detailed instructions")
    print("=" * 60 + "\n")
    
    return all_passed


def main():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("  Coqui TTS Integration Test")
    print("  Local Bank AI Agent")
    print("=" * 60)
    
    # Run checks
    results = []
    results.append(check_conda_env())
    results.append(check_tts_installed())
    results.append(check_reference_audio())
    results.append(check_server_script())
    results.append(test_tts_synthesis())
    
    # Print summary
    success = print_summary(results)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
