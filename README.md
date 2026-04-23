# 🏦 Local Bank AI Agent (v2.1.0)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3.0-green.svg)](https://python.langchain.com/)
[![Tests](https://img.shields.io/badge/tests-143%20passed-success.svg)](https://github.com/yourusername/local-bank-ai-agent/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Türkçe bankacılık işlemleri için doğal dil işleme özellikli, sesli komutlarla çalışan, **üretim ortamına hazır (production-ready)** yapay zeka bankacılık asistanı. 

Bu proje, bir banka müşterisinin "Hesabımda ne kadar var?", "Kredi kartı borcumu öde", "EFT yapmak istiyorum" gibi sesli komutlarını anlar, LangGraph ReAct Agent mimarisiyle doğru bankacılık API'sine karar verip işlemi yapar ve sonucu doğal bir insan sesiyle kullanıcıya geri okur.

---

## ✨ Öne Çıkan Özellikler (v2.1.0)

- **🎙️ Gelişmiş Sesli Arayüz (STT)**: Faster-Whisper ile anında Sesten-Metne çeviri. Türkçe finansal terimler için optimize edilmiştir.
- **🧠 Akıllı Karar Motoru**: LangGraph ReAct ajanı ile Ollama (Gemma4:26B-32K) entegrasyonu. **OpenAI Fallback** özelliği ile yerel LLM çökerse otomatik olarak bulut LLM'e (GPT-4o vb.) geçiş yapar.
- **🔊 Dinamik TTS (Metinden Sese) Yönlendiricisi**: 4 farklı TTS motoru desteklenir:
  - **Edge TTS** (Ücretsiz Microsoft Neural sesler - *Arayüzde Aktif*)
  - **Google Cloud TTS** (WaveNet sesler - *Arayüzde Aktif*)
  - **Coqui XTTS v2** (Yerel, ses klonlama özellikli, yüksek kalite. İzole Conda ortamında, Windows uyumluluğu için %100 güvenli dosya tabanlı mimariyle arka planda çalışır)
  - **Piper TTS** (Hafif, çevrimdışı yerel alternatif)
  *(Not: Karmaşıklığı önlemek adına kullanıcı arayüzünde sadece bulut/çevrimiçi motorlar listelenmektedir, yerel motorlar sistemde yedek (fallback) olarak veya API üzerinden kullanılmak üzere arka planda hazır bekler.)*
- **⚡ Asenkron Ses İşleme**: `AsyncAudioProcessor` ile `STT -> Agent -> TTS` boru hattı (pipeline) asenkron çalışır, sistemi bloklamaz.
- **🔐 Güvenlik ve Kimlik Doğrulama**: JWT (JSON Web Token) tabanlı kimlik doğrulama, SMS OTP simülasyonu, 11-haneli TCKN algoritmik doğrulaması.
- **📈 Monitoring ve Yük Testleri**: Prometheus `/metrics` endpointi ile detaylı sistem takibi ve `Locust` kullanılarak hazırlanmış yük testi (Load Testing) senaryoları.

---

## 🏗️ Sistem Mimarisi

**Clean Architecture** prensiplerine uygun olarak geliştirilmiştir:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          Presentation Layer                            │
│           FastAPI Web Server (v1 Endpoints) + HTML/JS UI               │
├────────────────────────────────────────────────────────────────────────┤
│                          Application Layer                             │
│     LangGraph Agent + Bank Tools Registry + Async Audio Processor      │
├────────────────────────────────────────────────────────────────────────┤
│                             Domain Layer                               │
│         Entities + Interfaces (IAccountService, IAuthService)          │
├────────────────────────────────────────────────────────────────────────┤
│                         Infrastructure Layer                           │
│   Mock Services + STT (Whisper) + TTS Router + LLM Router (Fallback)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Kurulum & Hızlı Başlangıç

### Gereksinimler
- **Python 3.10 veya 3.11** (Önerilen)
- **Ollama** arka planda çalışıyor olmalı (`http://localhost:11434`)
- FFmpeg (Ses dönüştürme işlemleri için sistem PATH'ine eklenmiş olmalı)

### 1. Ortam Kurulumu

```bash
# Sanal ortam oluşturun
conda create -n local_bank python=3.10 -y
conda activate local_bank

# Bağımlılıkları yükleyin
pip install -r requirements.txt
```

### 2. Konfigürasyon (.env)

```bash
cp .env.example .env
```
`.env` dosyasını açın ve güvenlik için `JWT_SECRET` değerini güvenli bir anahtarla değiştirin. 
İsteğe bağlı olarak OpenAI yedeklemesi için `OPENAI_API_KEY` ekleyebilirsiniz.

### 3. Sunucuyu Başlatma

```bash
python web_server.py
```

Tarayıcınızdan **`http://localhost:8000`** adresine giderek sesli asistanı kullanmaya başlayabilirsiniz!

---

## 📡 API Endpoints (v1)

Proje sürüm (versioning) kontrolünü destekler. Modern v1 endpointleri şunlardır:

| Method | Endpoint | Açıklama |
| :--- | :--- | :--- |
| GET | `/api/v1/health` | Sistem sağlık durumu ve bileşen kontrolleri |
| GET | `/api/v1/models` | Mevcut Ollama modellerini listele |
| POST | `/api/v1/auth/auth` | Kullanıcı temel kimlik denetimi (TCKN) |
| POST | `/api/v1/auth/verify`| OTP / Şifre kontrolü ve JWT Token üretimi |
| POST | `/api/v1/audio/process`| 🎙️ Uçtan uca ses işleme (STT -> AI -> TTS) |

*Not: Geriye dönük uyumluluk için eski root endpoint'leri (`/process_audio`, vb.) desteklenmeye devam etmektedir.*

---

## 📊 Metrikler, İzleme (Monitoring) & Yük Testi

### Prometheus Metrikleri
Sistem `prometheus-fastapi-instrumentator` ile varsayılan olarak `/metrics` adresinden metrik yayını yapar:
- `http_request_duration_seconds`
- İş mantığı (Business logic) hata oranları, yetkisiz erişim denemeleri.

### Locust ile Yük Testi (Load Testing)
Sistemin yoğun trafik altındaki davranışını test etmek için `tests/load/` dizininde Locust senaryoları mevcuttur.

```bash
# Locust web arayüzünü başlatmak için (http://localhost:8089):
locust -f tests/load/test_load_audio_processing.py --host=http://localhost:8000

# Headless (Arayüzsüz) 100 kullanıcı ile 5 dakikalık test:
locust -f tests/load/test_load_audio_processing.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 300s
```

---

## 🔊 Coqui XTTS v2 Kurulumu (İzole Ortam)

Coqui XTTS v2, paket çakışmalarını ve işletim sistemi tabanlı komut satırı (CLI) hatalarını engellemek için ana projeden tamamen **izole bir conda ortamında** ve **dosya tabanlı (file-based)** güvenli iletişim mimarisiyle çalışır.

Eğer arka planda bu motoru aktif etmek isterseniz:

1. Ayrı bir Conda ortamı kurun:
   ```bash
   conda create -n coqui_env python=3.10 -y
   conda activate coqui_env
   pip install TTS>=0.20.0
   ```
2. Ana projenin `.env` dosyasında ayarı aktifleştirin:
   ```ini
   TTS_ENABLE_COQUI_FALLBACK=true
   ```
*Ana uygulama, Coqui'ye gönderilecek metni önce geçici bir metin dosyasına yazar ve izole ortama "Bu dosyayı oku" komutunu gönderir. Bu sayede Türkçe karakterler, boşluklar veya tırnak işaretleri hiçbir işletim sistemi engeline takılmadan kusursuz sentezlenir.*

---

## 🧪 Testler (100% Passing)

Projedeki 143 testin tamamı (Birim testleri, API testleri, Mock servisleri, Session Manager vb.) başarıyla geçmektedir.

```bash
# Testleri çalıştırmak için
pytest

# Testleri detaylı görmek için
pytest -v
```

---

## 🤝 Katkıda Bulunma (Contributing)

Bu proje açık kaynak geliştirmeye uygundur. Katkıda bulunmak isterseniz:

1. Repoyu fork edin.
2. `feature/harika-ozellik` adında bir branch açın.
3. Geliştirme ortamı için `pip install -e ".[dev]"` komutuyla dev gereksinimlerini yükleyin.
4. Kodunuzu `pytest` ile test edin.
5. Pull Request gönderin.

*(Ayrıntılı yönergeler için lütfen proje kök dizinindeki veya GitHub Wiki'deki kaynaklara göz atın).*

---

## 📝 Lisans

Bu proje **MIT Lisansı** ile lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakabilirsiniz.

---

<p align="center">
  <b>Made with ❤️ for Turkish Banking Sector</b>
</p>
