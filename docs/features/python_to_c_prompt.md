**Task:** Migrate the Python mathematical method `[METHOD_NAME]` from the `compass` frontend to the `KeyFirmware` device. 

**Objective:** We must flawlessly translate the Python (NumPy/Pandas) logic into highly optimized C/C++ code. To guarantee that the data passed between Python and the device is PERFECT, all inputs and outputs must be strictly serialized as JSON.

Please execute the migration following these steps:

**1. Mathematical Translation (C Firmware)**
* Create `KeyFirmware/src/logic/[method_name].c`.
* Translate the core algorithm. Pay extreme attention to mathematical accuracy, replacing Pandas/NumPy functions with efficient C equivalents.
* Use the `cJSON` library to parse the incoming configuration and to generate the output JSON response (which could be an array, object, or single value depending on the method).
* **Memory Warning:** Ensure your static JSON receive/transmit buffers are sized appropriately for the payload of this specific method to prevent `ERR: OOM` crashes. Do not use dangerously small generic buffers.

**2. The JSON Chunking API (`KeySec` & Firmware)**
* Because the JSON configurations can be large, we use a 4-step chunking protocol (`INIT`, `CHUNK`, `PROCESS`, `READ`).
* Reserve 4 new contiguous hex IDs in `KeySec/core/transport.py` (e.g., `0x40-0x43`).
* Register these IDs in `KeyFirmware/src/rpc_router.h` and implement the 4 standard handlers in your `.c` file. 
* **Python API:** In `KeySec/api/compass_api.py`, write a wrapper `execute_[method_name](data_dict)` that serializes the full dictionary to JSON. Do NOT write manual chunking loops—simply delegate the call using `return self.chunk_transport.execute(...)` with your 4 new IDs.

**3. Frontend Integration (`compass`)**
* Locate `[METHOD_NAME]` in the `compass/app/` logic.
* Duplicate the method as `[METHOD_NAME]_device`. 
* At the top of the original function, insert: `if Functions.USE_DEVICE: return [METHOD_NAME]_device(app_conf)`.
* In the `_device` method, execute the API call, parse the returned JSON string back into the exact original Python data structures (DataFrame, dictionary, float, etc.), and return it.

**4. Testing Payload**
* If you need to generate a test payload, store it in `KeySec/api/test_payloads.py` using a **raw triple-quote block** (`r"""..."""`) to ensure Python does not illegally escape Windows file paths (`\\`).

Focus heavily on ensuring the C mathematical translation exactly mimics the Python output. Let me know if you have questions about the data types before you start writing the C logic.