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
SET q=%1
SET lang=en
SET keys=locate
SET filename=%keys%_log.log
ECHO Service-%keys% >> %filename%
ECHO Query: %q% >> %filename%
REM ===========================================================================
REM The number of calls is set. Never more than max
REM ===========================================================================
echo off
SET /a max=%2
ECHO Iterations-%max% >> %filename%
REM ===========================================================================
REM Building the command expresion.
REM ===========================================================================
SET curl_command=%NomApp% %modifier% %method%
REM ===========================================================================
REM ==================== Loop 1 to call the geolocator API ====================
REM ===========================================================================
SET urlAPI=https://fr59c5usw4.execute-api.ca-central-1.amazonaws.com/dev?
SET command=%curl_command% "%urlAPI%q=%q%%ampers%lang=%lang%%ampers%keys=%keys%"
echo %command%
ECHO Start API time-%Time% >> %filename%
@FOR /L %%G IN (1,1,%max%) DO (
echo loop: %%G
@%command%
)
ECHO Stop API time-%Time% >> %filename%
REM ================= Show the results at the end of the loop =================
ECHO completed %max% calls

REM ===========================================================================
REM ===================== Loop 2 to call the service url ======================
REM ===========================================================================
SET urlService="https://geogratis.gc.ca/services/geolocation/%lang%/locate?"
SET command=%curl_command% "%urlService%q=%q%
echo %command%
ECHO Start %keys% service time-%Time% >> %filename%
@FOR /L %%G IN (1,1,%max%) DO (
echo loop: %%G
@%command%
)
ECHO Stop %keys% service time-%Time% >> %filename%
REM ================= Show the results at the end of the loop =================
ECHO ===================== >> %filename%
ECHO completed %max% calls >> %filename%
ECHO. >> %filename%

REM ===========================================================================
REM We pause so that the window does not close 
REM ===========================================================================
