@echo off
rem     Скрипт запуска обработчика KUTIL
rem     *****************
rem     Структура запуска 
rem     PROC.bat <source_dir> <target_dir>
rem     <source_dir> - директория с исходным файлом kutdat
rem     <target_dir> - директория с исходным файлом korres
rem     ******************
rem     В процессе работы в директорию <target_dir> копируется файл kutdat
rem     создается директория out, производится обработка файла расчета korres в текущем его состоянии.
rem     Выходные файлы обработки, имеющие расширение .dat, перемещаются в данную директорию.
rem     ******************

rem set korpath=d:\DISK\Projects\KorsarPro\KORSAR-MT.exe
set kutpath=%~dp0..\kutil.exe

rem проверка наличия аргументов
if -%1-==-- (
echo No comand-line arguments provided. Exiting...
pause
exit
)

echo *** Checking source
if not exist %CD%\%1\kutdat (
  echo File %CD%\%1\kutdat does not exist
  goto :end
)

echo *** Copying files to calc dir...
if not exist %CD%\%2\kutdat (
  copy "%1\kutdat" "%2"
) else (
  replace "%1\kutdat" "%2"
)

echo *** Checking results
if not exist %CD%\%2\korres (
  echo File korres in %CD%\%2 does not exist
  goto :end
)

if exist %CD%\%2\kutlis (
  echo Kutlis detected. Deleting...
  del %CD%\%2\kutlis
)

echo *** Creating destination directory %2
set dirToCreate=%CD%\%2\out
set calcDir=%CD%\%2
echo dirToCreate:
echo %dirToCreate%

if not exist %dirToCreate% (
  md %dirToCreate%
  goto :1
) else (
  goto :2
)

rem директория out уже есть
:2 
REM echo "Output Dir already exists"
REM set /p ans=Overwrite? (y/n):
REM if %ans%==y (
  rd /q /s %dirToCreate%
  md %dirToCreate%
REM ) else (
  REM echo Exiting
  REM goto :end
REM )

rem  Копируем файлы из директории-исходника
rem  При наличии вспомогательных файлов добавить
rem  их в список ниже
:1
rem   Запускаем KUTIL в расчетной директории 
cd %calcDir%
echo *** Run KUTIL in %CD%
echo.
start /BELOWNORMAL /WAIT cmd /c ""%kutpath%" > log_proc.txt"
echo *** Processing finished
echo.

cd %dirToCreate%
echo *** Moving out files to %dirToCreate%
move "%calcDir%\*.dat"

:end
REM pause
exit


 






