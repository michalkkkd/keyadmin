# Numbalsoda Manual Installation Guide

## Background
The `compass` project heavily relies on the `numbalsoda` package for extreme math performance (as noted in `AGENTS.md`). However, `numbalsoda` is notably absent from the `requirements.txt` file.

This is because `numbalsoda` is currently installed manually in this project by directly injecting an unzipped wheel into the virtual environment, rather than using `pip install numbalsoda`.

## Why is it installed manually?
There is a known version mismatch issue between the newest Python releases (e.g., Python 3.14) and the pre-compiled `numbalsoda` wheels available on PyPI (which are often tagged for older versions like Python 3.10, i.e., `cp310`). 

Attempting to run `pip install numbalsoda` on a newer Python version will fail if pip cannot find a compatible pre-compiled `.whl` and the system lacks the C++ build tools required to compile it from source.

## The Workaround (Manual Installation)
Because the `numbalsoda` package relies heavily on pre-compiled `.dll` files (like `liblsoda.dll`) and pure Python wrapper scripts (like `driver.py`), the internal code is actually somewhat Python-version agnostic, despite the `.whl` being tagged strictly for `cp310`.

This allows us to bypass pip completely and manually copy the library into the environment.

### Step-by-Step Instructions for New Machines
If you are setting up the `compass` project on a new Windows machine (or a new VM) and encounter this error:
`ModuleNotFoundError: No module named 'numbalsoda'`

You can fix it by manually copying the unpacked `numbalsoda` wheel into your active virtual environment:

1. Locate the unzipped `cp310` wheel on your host machine (usually stored at `C:\Users\god\Documents\STORMPROJECTS\numbalsoda-0.3.4-cp310-cp310-win_amd64`).
2. Inside that directory, you will see two folders:
   - `numbalsoda`
   - `numbalsoda-0.3.4.dist-info`
3. Copy both of these folders.
4. Navigate to the `compass` project on your new machine/VM.
5. Paste the two folders directly into the `site-packages` directory of your active virtual environment:
   `compass\.venv\Lib\site-packages\`

Once the folders are physically present in `site-packages`, Python will immediately detect the module and the application will run flawlessly, bypassing the need for a complex C++ build environment or downgrading Python!
