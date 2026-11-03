@echo off
rem Baixa os eventos novos do produpark.com.br e regenera a planilha e a pagina.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python scripts\scrape.py dados || goto erro
python scripts\build.py dados || goto erro
copy /y dados\tempos_produpark.xlsx tempos_produpark.xlsx >nul
copy /y dados\dados.js docs\dados.js >nul
echo.
echo Pronto. Planilha: tempos_produpark.xlsx   Pagina: docs\index.html
echo Para publicar: git add -A ^&^& git commit -m "Atualiza tempos" ^&^& git push
pause
exit /b 0
:erro
echo Ocorreu um erro. Veja as mensagens acima.
pause
exit /b 1
