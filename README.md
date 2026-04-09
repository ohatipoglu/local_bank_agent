# 🏦 Local Bank AI Agent

*[🇹🇷 Türkçe açıklama için aşağı kaydırın / Scroll down for Turkish description](#🇹🇷-türkçe-açıklama)*

Voice-enabled AI banking assistant with natural language processing for Turkish banking operations.

## ✨ Features

- **🎙️ Voice Interface**: Speech-to-Text with Faster-Whisper (Turkish optimized)
- **🤖 AI Reasoning**: LangGraph ReAct agent with Ollama LLM integration
- **🔊 Text-to-Speech**: Google Cloud TTS with Piper offline fallback
- **🏦 Banking Operations**: Balance inquiry, credit card debt, EFT, Havale
- **🔐 Session Management**: Secure session handling with customer authentication
- **📊 Real-time Monitoring**: Web dashboard with activity terminal and log viewer
- **⚡ Performance**: Thread-safe agent caching, connection pooling, async processing
- **🛡️ Security**: Rate limiting, input validation, structured logging

## 🏗️ Architecture

Built with **Clean Architecture** principles:

```
┌─────────────────────────────────────────────┐
│          Presentation Layer                 │
│   FastAPI Web Server + HTML/JS UI          │
├─────────────────────────────────────────────┤
│          Application Layer                  │
│   LangChain Agent + Tools Registry          │
├─────────────────────────────────────────────┤
│           Domain Layer                      │
│   Entities + Interfaces (Ports)             │
├─────────────────────────────────────────────┤
│         Infrastructure Layer                │
│   Mock Services + STT/TTS Engines           │
└─────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Ollama running locally (`http://localhost:11434`)
- Google Cloud TTS credentials (JSON service account)

### Google Cloud TTS Setup

To use Google Cloud's high-quality Text-to-Speech voices, you need to configure a Service Account:
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Cloud Text-to-Speech API**.
3. Create a **Service Account** with TTS permissions.
4. Generate a new **JSON key** and download it to the project root directory.
5. Set the path in your `.env` file: `GOOGLE_APPLICATION_CREDENTIALS=./your-file-name.json`

### Installation

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run the server
uvicorn web_server:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in your browser.

### Docker Deployment

```bash
# Build image
docker build -t local-bank-ai-agent .

# Run container
docker run -p 8000:8000 \
  -v $(pwd)/local-bank-tts-*.json:/app/local-bank-tts-*.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/local-bank-tts-*.json \
  local-bank-ai-agent
```

## 📋 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main web UI |
| GET | `/logs` | Log monitoring dashboard |
| GET | `/api/models` | List available Ollama models |
| GET | `/api/logs` | Application logs (JSON) |
| GET | `/api/health` | Health check |
| GET | `/api/session/stats` | Session statistics |
| GET | `/events` | Server-Sent Events (real-time status) |
| POST | `/process_audio` | Process voice input (STT → Agent → TTS) |
| POST | `/api/auth` | Authenticate customer by ID |

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_session_manager.py -v
```

## 📁 Project Structure

```
local_bank_agent/
├── application/              # Business logic
│   ├── langchain_agent.py    # AI agent with ReAct reasoning
│   ├── tools_registry.py     # Banking tools (balance, EFT, etc.)
│   └── prompts.py            # Dynamic prompt generation
├── core/                     # Core utilities
│   ├── config.py             # Configuration management
│   ├── logger.py             # Structured logging
│   ├── exceptions.py         # Custom exceptions
│   ├── security.py           # Rate limiting, validation
│   ├── session_manager.py    # Session handling
│   └── agent_cache.py        # Thread-safe agent cache
├── domain/                   # Business entities
│   ├── entities.py           # User, Account, etc.
│   └── interfaces.py         # Service interfaces (ports)
├── infrastructure/           # External services
│   ├── mock_services.py      # Mock banking services
│   ├── tts_engine.py         # Google Cloud + Piper TTS
│   └── stt_engine.py         # Faster-Whisper STT
├── templates/                # HTML templates
├── tests/                    # Test suite
├── web_server.py             # FastAPI application
└── requirements.txt          # Python dependencies
```

## ⚙️ Configuration

All configuration via environment variables or `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to Google Cloud service account JSON | Required |
| `LLM_MODEL_NAME` | Ollama model name | `gemma4:26B-32K` |
| `STT_MODEL_SIZE` | Whisper model size | `large-v3` |
| `TTS_ENABLE_PIPER_FALLBACK` | Enable Piper TTS fallback | `true` |
| `RATE_LIMIT_REQUESTS` | Max requests per window | `30` |
| `MAX_AUDIO_SIZE_MB` | Max upload size (MB) | `10` |

See `.env.example` for all options.

## 🔒 Security

- **Rate Limiting**: 30 requests/minute per IP (configurable)
- **Input Validation**: File size limits (10MB), MIME type checking
- **Session Management**: UUID-based sessions with TTL expiration
- **Structured Logging**: Correlation IDs for request tracing
- **Credential Management**: Environment variables, never hardcoded

## 📊 Health Check

```bash
curl http://localhost:8000/api/health
```

Returns status of all components:
- STT engine (Whisper model)
- TTS engines (Google Cloud + Piper)
- Ollama API connectivity
- Session manager
- Agent cache

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for new functionality
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

## 🆘 Support

For issues or questions:
- Check `/api/health` endpoint for system status
- Review logs at `/logs` dashboard
- Open an issue on the repository

---

# 🇹🇷 Türkçe Açıklama

Türkçe bankacılık işlemleri için doğal dil işleme özellikli, sesli komutlarla çalışan yapay zeka bankacılık asistanı.

## ✨ Özellikler

- **🎙️ Sesli Arayüz**: Faster-Whisper ile Sesten Metne çeviri (Türkçe için optimize edilmiş)
- **🤖 Yapay Zeka Karar Mekanizması**: Ollama LLM entegrasyonu ile LangGraph ReAct ajanı
- **🔊 Metinden Sese**: Google Cloud TTS ve yedek olarak (offline) Piper TTS
- **🏦 Bankacılık İşlemleri**: Bakiye sorgulama, kredi kartı borcu öğrenme, EFT, Havale
- **🔐 Oturum Yönetimi**: Müşteri kimlik doğrulaması ile güvenli oturum kontrolü
- **📊 Gerçek Zamanlı İzleme**: Terminal ve log görüntüleme paneli sunan web dashboard
- **⚡ Performans**: Thread-safe (iş parçacığı güvenli) ajan önbelleği, asenkron işlemler
- **🛡️ Güvenlik**: Rate limiting (hız sınırlaması), veri doğrulama, yapılandırılmış loglama (structured logging)

## 🏗️ Mimari

Proje **Clean Architecture (Temiz Mimari)** prensiplerine uygun olarak geliştirilmiştir:

- **Presentation Layer (Sunum Katmanı):** FastAPI Web Sunucusu + HTML/JS Arayüz
- **Application Layer (Uygulama Katmanı):** LangChain Ajanı + Araç Kayıt Sistemi (Tools Registry)
- **Domain Layer (Etki Alanı Katmanı):** Varlıklar (Entities) + Arayüzler (Interfaces)
- **Infrastructure Layer (Altyapı Katmanı):** Sahte (Mock) Servisler + STT/TTS Motorları

## 🚀 Hızlı Başlangıç

### Gereksinimler

- Python 3.11+
- Bilgisayarınızda çalışan Ollama servisi (`http://localhost:11434`)
- Google Cloud TTS kimlik dosyası (JSON service account)

### Google Cloud TTS Kurulumu

Google Cloud'un yüksek kaliteli Text-to-Speech (Metin-Ses) altyapısını kullanmak için bir Servis Hesabı (Service Account) oluşturmanız gerekir:
1. [Google Cloud Console](https://console.cloud.google.com/) adresine gidin.
2. **Cloud Text-to-Speech API** servisini etkinleştirin.
3. TTS yetkilerine sahip bir **Service Account** (Servis Hesabı) oluşturun.
4. Yeni bir **JSON anahtarı (key)** oluşturup proje ana dizinine indirin.
5. İndirdiğiniz dosyanın adını `.env` dosyanızda güncelleyin: `GOOGLE_APPLICATION_CREDENTIALS=./dosya-adiniz.json`

### Kurulum

```bash
# Sanal ortam oluşturun
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Çevresel değişkenleri ayarlayın
cp .env.example .env
# .env dosyasını kendi ayarlarınıza göre düzenleyin

# Sunucuyu başlatın
uvicorn web_server:app --reload --host 0.0.0.0 --port 8000
```
Tarayıcınızda http://localhost:8000 adresini açarak uygulamayı kullanmaya başlayabilirsiniz.

## 📝 Lisans

Bu proje MIT Lisansı ile lisanslanmıştır. Daha fazla bilgi için `LICENSE` dosyasına (eğer mevcutsa) bakabilirsiniz.
