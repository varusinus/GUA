@echo off
title GUA - Real fine-tuning (QLoRA)
cd /d "%~dp0"
echo ==============================================================
echo   GUA REAL fine-tuning (QLoRA on your NVIDIA GPU)
echo   Steps: setup - build data - TRAIN - merge - import to Ollama.
echo   This uses your GPU heavily and can take a while. Grab a coffee.
echo ==============================================================
echo.
where python >nul 2>nul || (echo [!] Python not found. Install Python 3.10+ and retry. & pause & exit /b 1)

if not exist ".venv-train\Scripts\python.exe" (
  echo [1/7] Creating training environment .venv-train ...
  python -m venv .venv-train || (echo [!] venv creation failed & pause & exit /b 1)
)
call .venv-train\Scripts\activate

python -c "import torch" 2>nul
if errorlevel 1 (
  echo [2/7] Installing PyTorch with CUDA 12.1 ... big download, one time only.
  pip install torch --index-url https://download.pytorch.org/whl/cu121 || (echo [!] torch install failed & pause & exit /b 1)
)
echo [3/7] Installing training dependencies ...
pip install -r training\finetune\requirements-train.txt || (echo [!] dependency install failed & pause & exit /b 1)

echo.
echo Checking GPU:
python -c "import torch; print('  ', 'GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE (training will be very slow)')"
echo.

echo [4/7] Building the GUA dataset ...
python training\finetune\make_dataset.py || (echo [!] dataset build failed & pause & exit /b 1)

echo.
echo [5/7] === TRAINING (the real part - watch the loss drop) ===
python training\finetune\finetune_lora.py || (echo [!] TRAINING FAILED - copy the error above and paste it to your assistant. & pause & exit /b 1)

echo.
echo [6/7] Merging the trained weights into the model ...
python training\finetune\merge_lora.py || (echo [!] merge failed & pause & exit /b 1)

echo.
echo [7/7] Importing the fine-tuned model into Ollama as "gua-ft" ...
python training\finetune\make_ft_modelfile.py
ollama create gua-ft -f training\finetune\Modelfile.ft || (echo [!] Ollama import failed. If it says safetensors unsupported, see TRAINING.md GGUF fallback. & pause & exit /b 1)

echo.
echo ==============================================================
echo   DONE - your fine-tuned model "gua-ft" is now in Ollama.
echo   Run start_gua.bat - it will auto-detect and use gua-ft.
echo   GUA's version will auto-bump (new weights = real new version).
echo ==============================================================
pause
