@echo off
echo ====================================
echo Trading App - Quick Setup
echo ====================================
echo.

echo Step 1: Installing dependencies...
echo.
pip install flask flask-cors nsepython yfinance pandas numpy tensorflow pandas-ta-classic scikit-learn
echo.

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies
    echo Please check your Python and pip installation
    pause
    exit /b 1
)

echo.
echo ====================================
echo Step 2: Verifying installation...
echo ====================================
echo.
python -c "import pandas, flask, nsepython, yfinance; print('✓ All dependencies installed successfully!')"

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Verification failed
    pause
    exit /b 1
)

echo.
echo ====================================
echo Setup Complete!
echo ====================================
echo.
echo You can now:
echo 1. Run the server: python app.py
echo 2. Test a symbol: python test_symbol.py RELIANCE
echo 3. Access API at: http://localhost:5000/analyze/RELIANCE
echo.
echo Press any key to start the Flask server now, or Ctrl+C to exit
pause

echo.
echo Starting Flask server...
python app.py
