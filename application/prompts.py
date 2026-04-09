import os
import yaml
from functools import lru_cache
from typing import Dict, Any

# Uzman Tavsiyesi: Cache (Önbellek) Mekanizması Eklendi
@lru_cache(maxsize=1)
def load_prompts_from_yaml() -> Dict[str, Any]:
    """
    prompts.yaml dosyasını okur ve bellekte tutar.
    Sadece ilk çağrıda disk I/O işlemi yapar.
    Hata yönetimi eklendi.
    """
    yaml_path = os.path.join(os.path.dirname(__file__), "prompts.yaml")
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        # Fallback (Yedek) prompt'lar
        print(f"UYARI: {yaml_path} bulunamadı! Varsayılan (fallback) promptlar kullanılacak.")
        return {
            "base_prompt": "Sen Local Bank'ın yapay zeka asistanısın. Müşteriye yalnızca düz metin formatında kısa ve net cevaplar ver. Asla markdown kullanma.",
            "empathy_rule": "ÖNEMLİ: Müşteri duygusal bir durumdan (hastalık, üzüntü vb.) bahsederse, mutlaka insan gibi empati kur ve geçmiş olsun dile.",
            "strictness_levels": {
                1: "Sen esnek bir finansal danışmansın.",
                2: "Bankacılık terimleri hakkında bilgi verebilirsin.",
                3: "Müşterinin bankacılık sorularını kısaca yanıtla.",
                4: "Yalnızca sana verilen araçlarla yapabildiğin işlemleri yap. Empati kurma.",
                5: "Sen bir robotsun. Sadece bakiye, borç, EFT, havale işlemlerini yap. Başka hiçbir soruya cevap verme. Empati kurma."
            }
        }
    except yaml.YAMLError as e:
        print(f"HATA: {yaml_path} dosyası bozuk veya geçersiz YAML formatında: {e}")
        raise

def get_dynamic_prompt(strictness_level: int) -> str:
    """
    prompts.yaml dosyasından (önbellekten) kısıtlama seviyesine göre
    dinamik sistem promptunu oluşturur.
    """
    prompts = load_prompts_from_yaml()
        
    base_prompt = prompts.get("base_prompt", "")
    empathy_rule = prompts.get("empathy_rule", "")
    strictness_levels = prompts.get("strictness_levels", {})
    
    kural = strictness_levels.get(strictness_level, "Varsayılan bankacılık asistanı kurallarıyla hareket et.")
    
    # Uzman Tavsiyesi: Empati kuralını seviye 4 (Katı) ve 5 (Çok Katı) için kaldır.
    if strictness_level >= 4:
        return f"{base_prompt}\n{kural}"
    else:
        return f"{base_prompt}\n{empathy_rule}\n{kural}"
