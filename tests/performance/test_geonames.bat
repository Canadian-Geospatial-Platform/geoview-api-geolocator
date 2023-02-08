REM ===========================================================================
REM Enable local variables 
REM ===========================================================================
SETLOCAL ENABLEDELAYEDEXPANSION

REM ===========================================================================
REM Initialize constants, parameters and status variable
REM ===========================================================================
SET NomApp=curl
SET modifier=-X
SET method=GET
SET ampers=^&
SET q=meech
SET lang=en
SET keys=geonames
SET filename=%keys%_log.log
ECHO Service: %keys% >> %filename%
REM ===========================================================================
REM The number of calls is set. Never more than max
REM ===========================================================================
echo off
SET /a max=%1
ECHO Iterations: %max% >> %filename%

SET status=0
REM ===========================================================================
REM Building the command expresion.
REM ===========================================================================
SET curl_command=%NomApp% %modifier% %method%
REM ===========================================================================
REM ==================== Loop 1 to call the geolocator API ====================
REM ===========================================================================
SET urlAPI=https://fr59c5usw4.execute-api.ca-central-1.amazonaws.com/dev?
SET command=%curl_command% "%urlAPI%q=%q%%ampers%lang=%lang%%ampers%keys=%keys%"
ECHO Start URL_API time: %Time% >> %filename%
@FOR /L %%G IN (1,1,%max%) DO (
echo loop: %%G
@%command%
)
ECHO Stop URL_API time: %Time% >> %filename%
REM ================= Show the results at the end of the loop =================
ECHO completed %max% calls

REM ===========================================================================
REM ===================== Loop 2 to call the service url ======================
REM ===========================================================================
SET urlService=https://geogratis.gc.ca/services/geoname/%lang%/geonames.json?
SET command=%curl_command% "%urlService%q=%q%%ampers%lang=%lang%"
ECHO Start URL_Service time: %Time% >> %filename%
@FOR /L %%G IN (1,1,%max%) DO (
echo loop: %%G
@%command%
)
ECHO Stop URL_Service time: %Time% >> %filename%
REM ================= Show the results at the end of the loop =================
ECHO ===================== >> %filename%
ECHO completed %max% calls >> %filename%
ECHO. >> %filename%

REM ===========================================================================
REM We pause so that the window does not close 
REM ===========================================================================
