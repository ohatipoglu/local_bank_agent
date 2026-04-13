# 🏦 Local Bank AI Agent

Türkçe bankacılık işlemleri için doğal dil işleme özellikli, sesli komutlarla çalışan yapay zeka bankacılık asistanı.

## ✨ Özellikler

- **🎙️ Sesli Arayüz**: Faster-Whisper ile Sesten Metne çeviri (Türkçe için optimize edilmiş, large-v3 model)
- **🤖 Yapay Zeka**: LangGraph ReAct ajanı ile Ollama LLM entegrasyonu (Gemma4:26B-32K)
- **🔊 Metinden Sese**: 4 farklı TTS motoru:
  - **Google Cloud TTS** (birincil, WaveNet sesler)
  - **Coqui XTTS v2** (yerel, yüksek kalite, ses klonlama, tamamen çevrimdışı)
  - **Piper TTS** (çevrimdışı, hafif)
  - **Edge TTS** (Microsoft Neural, ücretsiz)
- **🏦 Bankacılık İşlemleri**: Bakiye sorgulama, kredi kartı borcu, EFT, Havale
- **🔐 Oturum Yönetimi**: Güvenli oturum ve müşteri kimlik doğrulama
- **📊 Web Dashboard**: Gerçek zamanlı aktivite terminali ve log görüntüleme
- **⚡ Performans**: Thread-safe ajan önbelleği, asenkron işlemler
- **🛡️ Güvenlik**: Rate limiting (30 req/60s), ses dosyası doğrulama, yapılandırılmış loglama

## 🏗️ Mimari

**Clean Architecture** prensiplerine uygun olarak geliştirilmiştir:

```
┌─────────────────────────────────────────────┐
│          Presentation Layer                 │
│   FastAPI Web Server + HTML/JS UI          │
├─────────────────────────────────────────────┤
│          Application Layer                  │
│   LangGraph Agent + Tools Registry         │
├─────────────────────────────────────────────┤
│           Domain Layer                      │
│   Entities + Interfaces (Ports)             │
├─────────────────────────────────────────────┤
│         Infrastructure Layer                │
│   Mock Services + STT/TTS Engines           │
└─────────────────────────────────────────────┘
```

## 🚀 Hızlı Başlangıç

### Gereksinimler

- **Python 3.11+**
- **Ollama** çalışıyor olmalı (`http://localhost:11434`)
- **Google Cloud TTS** credentials (JSON service account) - opsiyonel

### Kurulum

```bash
# Sanal ortam oluşturun
conda create -n local_bank python=3.11 -y
conda activate local_bank

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Çevresel değişkenleri ayarlayın
cp .env.example .env
# .env dosyasını kendi ayarlarınıza göre düzenleyin

# Sunucuyu başlatın
python web_server.py
```

Tarayıcınızda http://localhost:8000 adresini açın.

### Google Cloud TTS Kurulumu (Opsiyonel ama Önerilen)

Yüksek kaliteli WaveNet sesler için:
1. [Google Cloud Console](https://console.cloud.google.com/) adresine gidin
2. **Cloud Text-to-Speech API**'yi etkinleştirin
3. TTS yetkilerine sahip bir **Service Account** oluşturun
4. JSON key dosyasını proje dizinine indirin
5. `.env` dosyasında güncelleyin: `GOOGLE_APPLICATION_CREDENTIALS=./dosya-adiniz.json`

### Coqui XTTS v2 Kurulumu (Tamamen Çevrimdışı, Ses Klonlama)

Coqui XTTS v2, yüksek kaliteli Türkçe ses sentezi ve ses klonlama yeteneği sağlar:

**Özellikler:**
- 🎯 **Ses Klonlama**: 6-10 saniyelik ses örneği ile herhangi bir sesi klonlayın
- 📡 **Tamamen Çevrimdışı**: İnternet bağlantısı gerektirmez
- 🇹🇷 **Türkçe Desteği**: Mükemmel Türkçe dil modeli
- 🔒 **Gizlilik**: Tüm işlemler yerel olarak gerçekleşir

**Kurulum:**

```bash
# 1. Coqui environment oluşturun
conda create -n coqui_env python=3.10 -y
conda activate coqui_env
pip install TTS>=0.20.0

# 2. Referans ses dosyası hazırlayın
# - 6-10 saniye temiz Türkçe konuşma kaydedin
# - WAV formatında (16-bit, 22050 Hz, mono)
# - referans_ses.wav olarak proje kök dizinine kaydedin

# 3. .env dosyasında Coqui'yi aktif edin (zaten aktif)
# TTS_ENABLE_COQUI_FALLBACK=true
# COQUI_SPEAKER_WAV=./referans_ses.wav
```

Uygulamayı başlattığınızda Coqui otomatik olarak kullanılacak.

## 📋 API Endpoints

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/` | Ana web arayüzü |
| GET | `/logs` | Log izleme dashboard'u |
| GET | `/api/models` | Mevcut Ollama modellerini listele |
| GET | `/api/tts_engines` | Mevcut TTS motorlarını listele |
| GET | `/api/logs` | Uygulama logları (JSON) |
| GET | `/api/health` | Sağlık kontrolü |
| GET | `/events` | Server-Sent Events (gerçek zamanlı durum) |
| POST | `/process_audio` | Ses işleme (STT → Agent → TTS) |
| POST | `/api/auth` | Müşteri kimlik doğrulama (session-based) |
| POST | `/api/auth/verify` | Şifre/OTP doğrulama + JWT token alma |

## 🎛️ TTS Motorları

Uygulama 4 farklı metinden-ses motorunu destekler:

| Motor | Kalite | Çevrimdışı | Hız | Türkçe |
|-------|--------|------------|-----|--------|
| **Google Cloud TTS** | ⭐⭐⭐⭐⭐ | ❌ | Hızlı | ✅ Mükemmel |
| **Coqui XTTS v2** | ⭐⭐⭐⭐⭐ | ✅ | Orta | ✅ Çok İyi |
| **Edge TTS** | ⭐⭐⭐⭐ | ❌ | Hızlı | ✅ Çok İyi |
| **Piper TTS** | ⭐⭐⭐ | ✅ | Hızlı | ✅ İyi |

Web arayüzünden istediğiniz TTS motorunu seçebilirsiniz.

## 📁 Proje Yapısı

```
local_bank_agent/
├── application/              # Uygulama katmanı
│   ├── langchain_agent.py    # LangGraph AI ajanı
│   ├── tools_registry.py     # Bankacılık araçları
│   └── prompts.py            # Dinamik prompt üretimi
├── core/                     # Çekirdek modüller
│   ├── config.py             # Yapılandırma yönetimi
│   ├── logger.py             # Yapılandırılmış loglama
│   ├── exceptions.py         # Özel istisnalar
│   ├── security.py           # Rate limiting, doğrulama
│   ├── session_manager.py    # Oturum yönetimi
│   └── agent_cache.py        # Thread-safe ajan önbelleği
├── domain/                   # Etki alanı katmanı
│   ├── entities.py           # Varlıklar
│   └── interfaces.py         # Arayüzler (portlar)
├── infrastructure/           # Altyapı katmanı
│   ├── mock_services.py      # Sahte bankacılık servisleri
│   ├── tts_engine.py         # TTS motorları (4 adet)
│   ├── stt_engine.py         # Faster-Whisper STT
│   └── coqui_tts_server.py   # Coqui XTTS sunucu scripti
├── templates/                # HTML şablonları
├── static/                   # Statik dosyalar (CSS, JS)
├── models/                   # ML modelleri (Piper, referans ses)
├── tests/                    # Test dosyaları
├── web_server.py             # FastAPI uygulaması
├── .env.example              # Çevresel değişken şablonu
└── requirements.txt          # Python bağımlılıkları
```

## ⚙️ Yapılandırma

Tüm yapılandırma `.env` dosyası üzerinden yapılır:

| Değişken | Açıklama | Varsayılan |
|----------|----------|------------|
| `LLM_MODEL_NAME` | Ollama model adı | `gemma4:26B-32K` |
| `LLM_BASE_URL` | Ollama API URL'i | `http://localhost:11434` |
| `STT_MODEL_SIZE` | Whisper model boyutu | `large-v3` |
| `STT_DEVICE` | STT cihazı | `cpu` |
| `TTS_VOICE_NAME` | Google Cloud ses | `tr-TR-Wavenet-D` |
| `TTS_ENABLE_COQUI_FALLBACK` | Coqui'yi aktif et | `true` |
| `TTS_ENABLE_EDGE_FALLBACK` | Edge TTS'yi aktif et | `true` |
| `TTS_ENABLE_PIPER_FALLBACK` | Piper'ı aktif et | `true` |
| `RATE_LIMIT_REQUESTS` | Maksimum istek/süre | `30` |
| `MAX_AUDIO_SIZE_MB` | Maksimum ses boyutu | `10` |

Tüm seçenekler için `.env.example` dosyasına bakın.

## 🧪 Test

```bash
# Tüm testleri çalıştırın
pytest

# Kapsama raporuyla
pytest --cov=. --cov-report=html

# Belirli test dosyası
pytest tests/test_session_manager.py -v
```

## 🔒 Güvenlik

- **Rate Limiting**: IP başına 30 istek/dakika (yapılandırılabilir)
- **Ses Doğrulama**: Dosya boyutu limiti (10MB), MIME type kontrolü
- **Oturum Yönetimi**: UUID tabanlı oturumlar, TTL süresi ile sona erme
- **Yapılandırılmış Loglama**: İlişki ID'leri ile istek takibi
- **Gizli Bilgi Yönetimi**: Environment variables, asla hardcode değil
- **JWT Token Authentication**: `/api/auth/verify` endpoint'i ile şifre veya SMS OTP doğrulama

## 🚀 Production Readiness (Üretim Ortamına Hazırlık)

Bu proje **Production Ready** temel yapıdadır. Ancak yüksek trafikli üretim ortamları için aşağıdaki iyileştirmeleri öneriyoruz:

### 📦 Session Storage: SQLite (MVP) → Redis (Production)

**Mevcut Durum:** Oturum yönetimi SQLite ile yapılmaktadır. Bu, gelişim ve küçük ölçekli dağıtımlar için yeterlidir.

**Üretim Önerisi:** Yüksek trafikli ortamlarda SQLite üzerinde oluşan lock'lar performans darboğazı yaratabilir. Redis entegrasyonu ile:
- ✅ Yatay ölçeklendirme (multi-process / multi-pod)
- ✅ Düşük gecikme süresi (in-memory storage)
- ✅ Dağıtık oturum yönetimi
- ✅ Daha iyi concurrency handling

Redis kurulumu için `docker-compose.yml` dosyasında hazır Redis servisi bulunmaktadır.

### 🔐 Authentication: Mock → Gerçek Kimlik Doğrulama

**Mevcut Durum:** `MockAuthService` şifre ve OTP doğrulamasını simüle etmektedir.

**Üretim Önerisi:**
- Gerçek kullanıcı veritabanı entegrasyonu (PostgreSQL, MongoDB, vb.)
- SMS gateway entegrasyonu (Twilio, Netgsm, vb.)
- JWT secret'ı güçlü bir şekilde yönetin (environment variable + secret manager)
- JWT expiry süresini iş gereksinimlerinize göre ayarlayın

### ⚡ Rate Limiting: In-Memory → Redis-Backed

**Mevcut Durum:** Rate limiter uygulama belleğinde (dictionary) çalışmaktadır.

**Üretim Önerisi:** Multi-process veya container orchestrasyon (Kubernetes) ortamlarında Redis-backed rate limiting kullanın:
- `slowapi` kütüphanesi Redis storage ile
- veya API Gateway seviyesinde rate limiting (NGINX, Kong, APIM)

### 📊 Monitoring & Observability

- **Structured Logging:** Loguru ile JSON formatında loglama aktif
- **Metrics:** Prometheus metrikleri eklemek için `prometheus-fastapi-instrumentator` kullanın
- **Tracing:** OpenTelemetry ile distributed tracing ekleyin
- **Health Checks:** `/api/health` endpoint'i mevcut, Kubernetes liveness/readiness probe'larına entegre edin

### 🛡️ Error Handling: User-Friendly Messages

Tüm hatalar artık `core/error_handler.py` modülü üzerinden standardize edilmiştir:
- ✅ Kullanıcı dostu Türkçe mesajlar döndürülür
- ✅ Raw exception detayları (stack trace, path, library hataları) sadece server loglarında tutulur
- ✅ Internal server error'lar dışarı sızdırılmaz

## 🐳 Docker ile Dağıtım

```bash
# Image oluşturun
docker build -t local-bank-ai-agent .

# Container çalıştırın
docker run -p 8000:8000 \
  -v $(pwd)/local-bank-tts-*.json:/app/local-bank-tts-*.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/local-bank-tts-*.json \
  local-bank-ai-agent
```

Veya docker-compose ile:
```bash
docker-compose up -d
```

## 🤝 Katkıda Bulunma

1. Repoyu fork edin
2. Feature branch oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Yeni fonksiyonellik için test yazın
4. Değişiklikleri commit edin (`git commit -m 'Yeni özellik eklendi'`)
5. Branch'i push edin (`git push origin feature/yeni-ozellik`)
6. Pull Request açın

## 📝 Lisans

MIT Lisansı ile dağıtılmaktadır. Detaylar için `LICENSE` dosyasına bakın.

## 🆘 Destek

Sorunlar veya sorular için:
- `/api/health` endpoint'i ile sistem durumunu kontrol edin
- `/logs` dashboard'u ile logları inceleyin
- GitHub Issues'da bir issue açın

## 📊 Sistem Sağlık Kontrolü

```bash
curl http://localhost:8000/api/health
```

Tüm bileşenlerin durumunu döndürür:
- STT engine (Whisper model)
- TTS engines (Google Cloud, Coqui, Piper, Edge)
- Ollama API bağlantısı
- Session manager
- Agent cache

---

**Made with ❤️ for Turkish Banking**
