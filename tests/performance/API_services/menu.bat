echo off
REM ===========================================================================
REM Enable local variables 
REM ===========================================================================
SETLOCAL ENABLEDELAYEDEXPANSION

REM ===========================================================================
REM Initialize constants, parameters and status variable
REM ===========================================================================
SET /a max=1000
SET NOMINATIM_LOG=.\nominatim_log.log
SET GEONAMES_LOG=.\geonames_log.log
SET LOCATE_LOG=.\locate_log.log
SET NTS_LOG=.\nts_log.log
SET MERGED_FILE=.\merged_log.log
REM ===========================================================================
REM Remove old results
REM ===========================================================================
if exist %NOMINATIM_LOG% del %NOMINATIM_LOG%
if exist %GEONAMES_LOG% del %GEONAMES_LOG%
if exist %LOCATE_LOG% del %LOCATE_LOG%
if exist %NTS_LOG% del %NTS_LOG%
if exist %MERGED_FILE% del %MERGED_FILE%
REM ===========================================================================
REM Define the Services menu options
REM ===========================================================================
:NEW_TEST
cls
echo NEW TEST
echo
echo Select the service(s) to test
echo 1 - Nominatim
echo 2 - Geonames
echo 3 - Locate
echo 4 - Nts
echo 5 - All
echo 9 - exit
echo.
REM ===========================================================================
REM Define actions for each option
REM ===========================================================================
set /p M= Enter the digit of your selecton (9 to finish) :
if %M%==9 goto EOF
if %M% GEQ 6 goto NEW_TEST
:QUERY
echo.
SET q=""
set /p q= Enter the query text :
if %q%=="" goto QUERY
echo.
SET calls=1
set /p calls= Enter the number of calls to be performed (max=1000). then press 'return' :
if %max% LSS %calls% (SET /a calls=%max%)
if %M%==1 goto NOMINATIM
if %M%==2 goto GEONAMES
if %M%==3 goto LOCATE
if %M%==4 goto NTS
if %M%==5 goto NOMINATIM
echo.
goto menu_services
:NOMINATIM
call test_nominatim %q% %calls%
if %M%==1 goto NEW_TEST
:GEONAMES
call test_geonames  %q% %calls%
if %M%==2 goto NEW_TEST
:LOCATE
call test_locate  %q% %calls%
if %M%==3 goto NEW_TEST
:NTS
call test_nts  %q% %calls%
goto NEW_TEST
:EOF
set /p Y=Merge log files into one (y/n)? :
echo on
if %Y% NEQ y goto BYE
if exist %NOMINATIM_LOG% type %NOMINATIM_LOG% >>  %MERGED_FILE%
if exist %GEONAMES_LOG% type %GEONAMES_LOG% >>  %MERGED_FILE%
if exist %LOCATE_LOG% type %LOCATE_LOG% >>  %MERGED_FILE%
if exist %NTS_LOG% type %NTS_LOG% >>  %MERGED_FILE%
:BYE 
ECHO BYE
