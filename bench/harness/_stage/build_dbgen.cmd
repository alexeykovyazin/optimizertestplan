@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64 >nul 2>&1
cd /d E:\Projects_Big\optimizertestplan\third_party\tpch-dbgen
cl /nologo /O2 /DDBNAME=\"dss\" /DWIN32 /DORACLE /DTPCH /DRNG_TEST /D_FILE_OFFSET_BITS=64 /Fedbgen.exe build.c driver.c bm_utils.c rnd.c print.c load_stub.c bcd2.c speed_seed.c text.c permute.c rng64.c
cl /nologo /O2 /DDBNAME=\"dss\" /DWIN32 /DORACLE /DTPCH /DRNG_TEST /D_FILE_OFFSET_BITS=64 /Feqgen.exe build.c bm_utils.c qgen.c rnd.c varsub.c text.c bcd2.c permute.c speed_seed.c rng64.c
