@echo off
echo ==============================================
echo  Setting up Mastering Vocabulary Environment...
echo ==============================================

:: 1. Create the virtual environment named 'venv'
echo Creating virtual environment...
python -m venv vocabulary_venv

:: 2. Activate it temporarily to upgrade pip
echo Upgrading pip...
call vocabulary_venv\Scripts\activate.bat
python -m pip install --upgrade pip

:: 3. Install requirements inside the venv
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo ==============================================
echo  Setup Complete! 
echo  You can now delete this file if you want, 
echo  or keep it in case you need to reinstall.
echo ==============================================
pause