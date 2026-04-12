# 📖 Local Bank AI Agent - Kullanım Talimatları

## 🎯 Hızlı Başlangıç (5 Dakika)

### 1. Gereksinimler

Uygulamayı çalıştırmadan önce sisteminizde şunlar olmalı:
- ✅ Python 3.10 veya üzeri
- ✅ Ollama çalışıyor olmalı (`http://localhost:11434`)
- ✅ Google Cloud TTS credentials (JSON dosyası) - opsiyonel

### 2. Kurulum Adımları

#### Adım 1: Bağımlılıkları Yükleyin

```bash
# Proje dizinine gidin
cd C:\Projects\anaconda_projects\local_bank\local_bank_agent

# Sanal ortam oluşturun (ilk kez ise)
python -m venv venv

# Sanal ortamı aktif edin
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Tüm bağımlılıkları yükleyin
pip install -r requirements.txt
```

#### Adım 2: .env Dosyasını Ayarlayın

```bash
# .env.example dosyasını kopyalayın
cp .env.example .env

# .env dosyasını düzenleyin
# Tercih ettiğiniz editörle açın (notepad, vscode, vb.)
```

**Minimum gerekli ayarlar:**

```env
# Google Cloud TTS (Opsiyonel ama önerilir)
GOOGLE_APPLICATION_CREDENTIALS=./local-bank-tts-424c208f9a50.json

# LLM Settings
LLM_MODEL_NAME=gemma4:26B-32K
LLM_BASE_URL=http://localhost:11434
```

#### Adım 3: Ollama'yı Başlatın

```bash
# Ollama servisinin çalıştığından emin olun
# Terminalde şu komutu test edin:
curl http://localhost:11434/api/tags

# Modeli indirin (ilk kez ise):
ollama pull gemma4:26B-32K
```

#### Adım 4: Uygulamayı Başlatın

```bash
# Ana uygulamayı başlatın
python web_server.py

# VEYA uvicorn ile:
uvicorn web_server:app --reload --host 0.0.0.0 --port 8000
```

#### Adım 5: Tarayıcıda Açın

```
http://localhost:8000
```

🎉 **Tebrikler! Uygulama çalışıyor!**

---

## 🏦 Bankacılık İşlemleri Kullanımı

### Müşteri Girişi

Uygulama açıldığında müşteri kimliği ile giriş yapın:

**Test Müşterileri:**
- TC Kimlik: `10000000146` → Ahmet Yılmaz
- TC Kimlik: `20000000132` → Fatma Demir

### Sesli Komutlar

Mikrofon ikonuna tıklayın ve aşağıdaki komutları söyleyin:

#### 1. Bakiye Sorgulama
```
"Bakiyem ne kadar?"
"Hesabımda kaç param var?"
"Ne kadar param var?"
```

#### 2. Kredi Kartı Borcu
```
"Kredi kartı borcum ne kadar?"
"Kart ekstremi göster"
"Son ödeme tarihi ne zaman?"
```

#### 3. Hesap Listeleme (YENİ!)
```
"Hesaplarım neler?"
"Tüm hesaplarımı göster"
"Hangi hesaplarım var?"
```

#### 4. İşlem Geçmişi (YENİ!)
```
"Son işlemlerimi göster"
"Hesap hareketlerim neler?"
"İşlem geçmişimi getir"
```

#### 5. EFT İşlemi
```
"EFT yapmak istiyorum"
"TR123456789012345678901234 IBAN'ına 1000 TL gönder"
```

#### 6. Havale İşlemi
```
"Havale yapmak istiyorum"
"123456789 hesap numarasına 500 TL gönder"
```

#### 7. Kredi Kartı Ödeme (YENİ!)
```
"Kredi kartı borcumu öde"
"Kart borcumun tamamını yatır"
"Kredi kartıma 500 TL öde"
```

---

## 🔧 Geliştirme Modu

### Testleri Çalıştırma

```bash
# Tüm testleri çalışırın
pytest tests/ -v

# Coverage ile testler
pytest tests/ -v --cov=. --cov-report=term-missing

# Belirli bir test dosyası
pytest tests/test_config.py -v

# Coverage raporu (HTML)
pytest --cov=. --cov-report=html
# Rapor: htmlcov/index.html dosyasını tarayıcıda açın
```

### Kod Kalitesi Kontrolü

```bash
# Linting (Ruff)
ruff check .

# Otomatik düzeltme
ruff check --fix .

# Format kontrolü (Black)
black .

# Tip kontrolü (MyPy)
mypy application core domain infrastructure
```

### Pre-commit Hooks Kurulumu

```bash
# Pre-commit yükleyin
pip install pre-commit

# Hooks'u kurun
pre-commit install

# Tüm dosyalarda çalıştırın
pre-commit run --all-files
```

---

## 🐳 Docker ile Çalıştırma

### Yöntem 1: Docker Image

```bash
# Image oluşturun (ilk kez ise)
docker build -t local-bank-ai-agent:latest .

# Container çalıştırın
docker run -p 8000:8000 ^
  -v %CD%\local-bank-tts-*.json:/app/credentials.json:ro ^
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json ^
  local-bank-ai-agent:latest
```

### Yöntem 2: Docker Compose

```bash
# Tüm servisleri başlatın
docker-compose up -d

# Logları görüntüleyin
docker-compose logs -f app

# Durdurun
docker-compose down
```

**Not:** Docker kullanırken Ollama'nın `host.docker.internal` adresinden erişilebilir olması gerekir.

---

## ⚙️ Gelişmiş Ayarlar

### API Key Güvenliği (Opsiyonel)

Endpoint'leri korumak için API key kullanın:

1. `.env` dosyasına ekleyin:
```env
API_KEY=sizin-gizli-anahtariniz-123
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

2. Uygulamayı yeniden başlatın

3. API isteklerinde header kullanın:
```bash
curl -H "X-API-Key: sizin-gizli-anahtariniz-123" \
     http://localhost:8000/api/health
```

### TTS Motorları

Uygulama birden fazla TTS motorunu destekler:

| Motor | Kalite | Offline | Kurulum |
|-------|--------|---------|---------|
| Google Cloud TTS | ⭐⭐⭐⭐⭐ | ❌ | Credentials gerekli |
| Piper TTS | ⭐⭐⭐ | ✅ | Otomatik |
| Edge TTS | ⭐⭐⭐⭐ | ❌ | Otomatik (internet gerekli) |
| Coqui XTTS | ⭐⭐⭐⭐⭐ | ✅ | Ayrı kurulum gerekli |

Web arayüzünden TTS motorunu seçebilirsiniz.

### Performans İyileştirmeleri

Daha hızlı yanıt süreleri için:

```env
# Daha küçük STT modeli (daha hızlı, biraz daha az doğru)
STT_MODEL_SIZE=medium
STT_DEVICE=cuda  # GPU varsa

# Daha küçük LLM modeli
LLM_MODEL_NAME=gemma:7b

# Timeout değerlerini azaltın
LLM_TIMEOUT_SECONDS=60
```

---

## 📊 API Endpoint'leri

### Web Arayüzü
| Method | URL | Açıklama |
|--------|-----|----------|
| GET | `http://localhost:8000/` | Ana sayfa |
| GET | `http://localhost:8000/logs` | Log dashboard |

### API
| Method | URL | Açıklama |
|--------|-----|----------|
| GET | `/api/health` | Sistem sağlığı |
| GET | `/api/models` | Mevcut Ollama modelleri |
| GET | `/api/tts_engines` | Mevcut TTS motorları |
| GET | `/api/logs` | Uygulama logları |
| GET | `/api/session/stats` | Session istatistikleri |
| POST | `/process_audio` | Ses işleme (STT → AI → TTS) |
| POST | `/api/auth` | Müşteri doğrulama |
| GET | `/events` | SSE gerçek zamanlı güncellemeler |

### Sağlık Kontrolü Örneği

```bash
curl http://localhost:8000/api/health
```

**Yanıt:**
```json
{
  "status": "healthy",
  "components": {
    "stt": {
      "status": "healthy",
      "model": "large-v3",
      "device": "cpu"
    },
    "tts": {
      "status": "healthy",
      "engines_available": 3,
      "engines": ["google", "piper", "edge"],
      "default_engine": "google"
    },
    "ollama": {
      "status": "healthy",
      "base_url": "http://localhost:11434"
    }
  }
}
```

---

## 🐛 Sorun Giderme

### Problem: "pydantic-settings not found" hatası

**Çözüm:**
```bash
pip install pydantic-settings
```

### Problem: Ollama'ya bağlanılamıyor

**Çözüm:**
```bash
# Ollama çalışıyor mu kontrol edin
curl http://localhost:11434/api/tags

# Ollama'yı başlatın
ollama serve

# Model indirilmiş mi kontrol edin
ollama list

# Model yoksa indirin
ollama pull gemma4:26B-32K
```

### Problem: Google TTS çalışmıyor

**Çözüm:**
1. Credentials dosyasının varlığını kontrol edin
2. `.env` dosyasındaki yolu doğrulayın
3. Google Cloud Console'da Text-to-Speech API'nin aktif olduğundan emin olun

**Alternatif:** Piper veya Edge TTS kullanın (otomatik fallback)

### Problem: Whisper model yüklenmesi çok yavaş

**Çözüm:**
```env
# Daha küçük model kullanın
STT_MODEL_SIZE=medium
# VEYA
STT_MODEL_SIZE=small

# GPU kullanın (varsa)
STT_DEVICE=cuda
STT_COMPUTE_TYPE=float16
```

### Problem: Testler başarısız oluyor

**Çözüm:**
```bash
# Bağımlılıkları kontrol edin
pip install -e ".[dev]"

# Testleri verbose modda çalıştırın
pytest tests/ -v --tb=long

# Belirli bir test dosyası
pytest tests/test_config.py -v
```

### Problem: CORS hatası alınıyor

**Çözüm:**
```env
# .env dosyasında
CORS_ORIGINS=*  # Geliştirme için
# VEYA
CORS_ORIGINS=http://localhost:3000,http://localhost:8000  # Production için
```

---

## 📝 Logları Görüntüleme

### Web Arayüzü
```
http://localhost:8000/logs
```

### API üzerinden
```bash
curl http://localhost:8000/api/logs?limit=50
```

### Konsol
Uygulama çalışırken terminalde canlı log görünür.

---

## 🎓 İpuçları

### 1. Session Yönetimi
- Her oturum 1 saat (3600 saniye) geçerlidir
- Otomatik olarak yenilenir
- Sayfayı yenilediğinizde oturum devam eder

### 2. Ses Kalitesi
- Net ve yavaş konuşun
- Arka plan gürültüsünü azaltın
- Türkçe kelimeler kullanın

### 3. Güvenlik
- Production'da mutlaka `API_KEY` ayarlayın
- `DEBUG=false` kullanın
- Google credentials dosyasını asla commit etmeyin

### 4. Performans
- İlk yükleme yavaş olabilir (modeller yükleniyor)
- Sonraki istekler daha hızlıdır (cache)
- GPU varsa kullanın

---

## 📚 Kaynaklar

### Dokümantasyon
- `README.md` - Ana proje dokümantasyonu
- `CONTRIBUTING.md` - Katkıda bulunma rehberi
- `IMPLEMENTATION_SUMMARY.md` - Değişikliklerin özeti
- `QUICK_START.md` - Hızlı başlangıç rehberi

### Test Müşterileri
| TC Kimlik | İsim | Hesap |
|-----------|------|-------|
| 10000000146 | Ahmet Yılmaz | Vadesiz: 45,500 TRY |
| 20000000132 | Fatma Demir | Vadeli: 128,750 TRY |

### Varsayılan Değerler
- Kredi Kartı Borcu: ~12,450 TRY
- Son Ödeme: 15 Nisan
- EFT/Havale Limit: Kontrolsüz (mock)

---

## ✅ Kontrol Listesi

Uygulamayı kullanmaya başlamadan önce:

- [ ] Python 3.10+ yüklü
- [ ] Bağımlılıklar yüklü (`pip install -r requirements.txt`)
- [ ] Ollama çalışıyor
- [ ] Model indirilmiş (`ollama pull gemma4:26B-32K`)
- [ ] `.env` dosyası yapılandırılmış
- [ ] Google Cloud credentials ayarlanmış (opsiyonel)
- [ ] Uygulama başlatılmış (`python web_server.py`)
- [ ] Tarayıcıda `http://localhost:8000` açılmış

---

## 🆘 Yardım

Sorun mu var?

1. **Sağlık kontrolü:** `http://localhost:8000/api/health`
2. **Loglar:** `http://localhost:8000/logs`
3. **Dokümantasyon:** `IMPLEMENTATION_SUMMARY.md`
4. **Issue açın:** GitHub Issues

---

**Keyifli kullanımlar! 🎉**

Herhangi bir sorunuz olursa yukarıdaki kaynaklara başvurun veya GitHub Issues'da sorun.
