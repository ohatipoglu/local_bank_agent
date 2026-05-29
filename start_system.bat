@echo off
setlocal

echo [1/2] Ollama arka planda baslatiliyor...
:: Ollama optimizasyon ayarlari
set OLLAMA_VULKAN=1
set OLLAMA_KEEP_ALIVE=-1
set OLLAMA_NUM_PARALLEL=2
set OLLAMA_HOST=127.0.0.1:11434

:: "start /B" komutu Ollama'yi yeni bir pencere acmadan, mevcut pencerenin arka planinda calistirir.
start /B "" ollama serve

echo Ollama'nin hazir olmasi icin bekleniyor...
timeout /t 5 /nobreak > nul

echo.
echo [2/2] Web sunucusu baslatiliyor...
:: Python sunucusunu ayni pencerede baslatiyoruz
python web_server.py

:: Eger web sunucusu kapanirsa, kullaniciya bir mesaj ver
echo.
echo Web sunucusu kapatildi.
echo Not: Arka planda calisan Ollama servisini kapatmak icin gorev yoneticisinden (Task Manager) 'ollama.exe' islemini sonlandirabilirsiniz.
pause
