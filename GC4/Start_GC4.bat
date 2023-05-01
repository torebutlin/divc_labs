@echo off
title start_GC4_notebook

xcopy \\fileserv\public\teach\mechanics_labs\GC4\GC4_Notebook.ipynb \\ifs.eng.cam.ac.uk\users\%username%\ts-home\lab_GC4\

call C:\ProgramData\Anaconda3\Scripts\activate.bat
call conda activate p10
call jupyter notebook --notebook-dir=\\ifs.eng.cam.ac.uk\users\%username%\ts-home\lab_3C6\
