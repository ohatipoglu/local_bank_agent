import os
import shutil

def clean_project():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Silinecek gereksiz ve eski dosyaların listesi
    files_to_remove = [
        "main_backup.py", 
        "application.log", 
        "indir_ses.py",
        "temp_input.wav",
        "temp_output.wav",
        "web_response.wav",
        "web_temp_user_voice.wav",
        "main.py",
        os.path.join("application", "call_manager.py"),
        os.path.join("infrastructure", "llm_engine.py")
    ]
    
    # UUID ile olusmus, onceden kalma hatali temp WAV dosyalarini da bul ve sil
    for f in os.listdir(root_dir):
        if f.startswith("web_temp_") or f.startswith("web_response_") or f.startswith("piper_output_") or f.startswith("google_output_"):
            if f.endswith(".wav") and f not in files_to_remove:
                files_to_remove.append(f)

    # Dosyalari Sil
    for f in files_to_remove:
        file_path = os.path.join(root_dir, f)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Silindi: {f}")
            except Exception as e:
                print(f"Silinemedi: {f} - {e}")
                
    # 2. PyCache klasorlerini temizle
    for root, dirs, files in os.walk(root_dir):
        for d in dirs:
            if d == "__pycache__":
                cache_dir = os.path.join(root, d)
                try:
                    shutil.rmtree(cache_dir)
                    print(f"Önbellek (Cache) Temizlendi: {cache_dir}")
                except Exception as e:
                    print(f"Önbellek temizlenemedi: {cache_dir} - {e}")

if __name__ == "__main__":
    print("--- Proje Temizligi Basliyor ---")
    clean_project()
    print("--- Temizlik Tamamlandi ---")
