@echo off
rem     Скрипт запуска задачи KORSAR
rem     *****************
rem     Структура запуска 
rem     START.bat <source_dir> <final_dir> <targetcore>
rem     <source_dir> - директория с исходными файлами kordat и kutdat
rem     <final_dir> - директория, куда нужно поместить результаты расчета
rem     <targetcore> - ядро, на которое нужно поставить расчет
rem     ******************
rem     В процессе расчета в текущей директории расположения START.bat 
rem     создается директория <final_dir>, в которую копируются исходные файлы kordat, kordat_restart,
rem     kutdat, korsav. Расчет производится в <final_dir> с записью логов log_start.txt и log_calc.txt
rem     Для остановки расчета в консоли расчета набрать ctrl+Break и exit   
rem     ******************

rem set korpath=d:\DISK\Projects\KorsarPro\KORSAR-MT.exe
set korpath=%~dp0..\korsar.exe

rem проверка наличия аргументов
if -%1-==-- (
echo No comand-line arguments provided. Exiting...
pause
exit
)

echo *** Creating destination directory %2
set dirToCreate=%CD%\%2
echo dirToCreate:
echo %dirToCreate%

if %1==%2 (
echo Run KORSAR in %dirToCreate%
goto :101
)

if not exist %dirToCreate% (
  md %dirToCreate%
  goto :1
) else (
  goto :2
)

rem директория уже есть
:2 
echo "Output Dir already exists"
set /p ans=Overwrite? (y/n):
if %ans%==y (
  rd /q /s %dirToCreate%
  md %dirToCreate%
) else (
  echo Exiting
  goto :end
)

rem  Копируем файлы из директории-исходника
rem  При наличии вспомогательных файлов добавить
rem  их в список ниже
:1
echo *** Copying files to calc dir...
copy "%1\kordat" "%2"

:101
rem   Запускаем КОРСАР в расчетной директории 
cd %dirToCreate%
echo *** Run KORSAR in %cd%
echo Starting KORSAR %DATE% %TIME% >log_start.txt 
echo.
echo Source directory: %1% >>log_start.txt 
echo.

if not -%3-==-- (
    rem Запуск на конкретном ядре с перенаправлением вывода
    start /BELOWNORMAL /WAIT /AFFINITY %3 cmd /c ""%korpath%" > log_calc.txt"
) else (
    rem Запуск без привязки к ядру с перенаправлением вывода
    start /BELOWNORMAL /WAIT cmd /c ""%korpath%" > log_calc.txt"
)

echo *** Calculation finished
echo.
echo Finishing KORSAR %DATE% %TIME% >>log_start.txt 

:end
REM pause
exit







