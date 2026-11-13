# C++ ODE models (`compass_models.dll`): speed work and how to keep it safe

`USE_PRECOMPILED_MODELS = 2` solves `model_V`, `model_PK_18/19/22` with the C++ `LSODA` in
`app/level_builder/` (sources: `LSODA.cpp/.h`, `model_*.cpp`, `compass_models.cpp`, `x87_pow.asm`, `sysmath.h`,
`model_V_exact.cpp`). Build with `app/level_builder/build_compass_models/build.bat` (runs `ml64` for `x87_pow.asm`, then
`cl`, writes `app/level_x/compass_models.dll`). The same `lsoda_wrapper` is also called by `Sim_Rapid.dll` /
`safe_space_calc.dll`.

## Rule: the numbers must equal the JIT (numba `liblsoda.dll`) ones, bit for bit
The Perfect IO references come from the JIT path. `safe_space_calc` rounds `delta_Cmax_perc` to 3 decimals, so a
difference of one unit in the last place anywhere in an ODE solve can flip a digit in its output
(`res_pooled_GE_types.data[r][9]` / `[10]`, abs diff exactly 0.001 in the divergence table). Speed work must therefore keep
every output **bit-identical**. No `/fp:fast`, no FMA / `/arch:AVX2` (older CPUs crash with
`EXCEPTION_ILLEGAL_INSTRUCTION`, see compilation.md Error 21), no reordering of sums.

## Why C++ and JIT used to differ (found 2026-10-27, fixed)
Measured on the stored payloads: only ~90% of the PK outputs were bit-identical to the JIT, and 24 of 36 stored
`safe_space_calc` payloads changed a digit. Two independent causes:
1. **LSODA step-size `pow`.** `liblsoda.dll` (the JIT reference) is built with MinGW and carries its own `pow`: integer
   exponents by repeated squaring (negative ones on the reciprocal), `y == 0.5` as an x87 `fsqrt`, everything else as
   `exp2l(y * log2l(x))` on the x87 unit (`fyl2x`/`fyl2xp1`, `f2xm1`, `fscale`). The UCRT `pow` used by MSVC rounds
   differently in the last bit, which changes LSODA's step-size choice. `LSODA.cpp` now calls `lsoda_pow`, which reproduces
   that code instruction for instruction (`x87_pow.asm`). Do not "simplify" it back to `std::pow`.
2. **RHS `pow` / `exp` in `model_PK_*.cpp`.** numba calls the `pow`/`exp` of the system `ucrtbase.dll`. The statically linked
   CRT of the dll (`/MT`) is another build of them and differs in about 1 of 5000 calls. `sysmath.h` looks the two
   functions up in `ucrtbase.dll` at load time (`sys_pow`, `sys_exp`), which keeps `/MT` (no dependency on the VC runtime
   redistributable, `/MD` would need `msvcp140.dll`) and matches the JIT.
3. **`model_V` exact solve is OFF.** `model_V_exact.cpp` (matrix exponential, ~7x faster than LSODA) differs from the JIT at the
   1e-6 level; that alone flips digits in 24 of 36 stored `safe_space_calc` payloads. `set_exact_v(1)` (exported) switches it on
   again if a deployment accepts tiny differences. Default `0` = LSODA, bit-identical.

Result (10000 stored payloads per model, `_internal/tools/bench_cpp_models.py`): `model_V`, `model_PK_18/19/22` are **100.000%
bit-identical** to the JIT, and all 36 stored `safe_space_calc` payloads reproduce their expected output with 0 differences.

## `Cs = nan` in `safe_space_calc.dll` (found 2026-11-05, fixed)
`safe_space_calc.cpp` marks a missing solubility (`ssd_CsS` / `ssd_CsI` = `'nan'`) as `-1`. `NW_rk4` reads `-1` as the
simplified Noyes-Whitney, but `-1` was also passed to `Sim_Rapid_C`, where `model_PK_19` dissolves without a limit only
for `Cs > 100000` and a negative Cs dissolves nothing. Python (`Sim_Rapid.py`, `sim_rapid_cpp.py`) passes `10000000`.
Every SSD test with `CsS = nan` (007, 017, 019, 022) gave other numbers; with both Cs nan (011) `Cmax_Ref = 0` gave
NaN deltas, `run_ge_loop` never wrote its uninitialized `max_row`, and `r.BE.decode()` raised `UnicodeDecodeError`.
Fix: `pk_cs()` turns `-1` into `1e7` at both `Sim_Rapid_C` calls, `GeResult` is zeroed and a NaN delta still fills the
row (pandas `idxmax` skips NaN). The 36 payloads of the 2026-10-27 replay had no `nan` case, so it had not caught this.

## No `thread_local` in the dlls (found 2026-11-06, fixed)
The three dlls are bundled into the Themida-protected exe (`--themida-bundled-files`) and loaded from memory. That loader
does not support a static TLS section: with `thread_local` in `compass_models.cpp` / `model_V_exact.cpp` the dll had a TLS
directory, `ctypes.CDLL` in the exe looped forever on `Windows fatal exception: code 0xc0000026` (faulthandler printed every
thread's stack each time, in every test worker), while the same dll worked from Python. The pool / a locked cache replaced
them (bit-identical, PK solves a bit faster). Rules for all dlls in `app/level_x/`: no `thread_local` / `__declspec(thread)`,
no function-local statics with dynamic initialization (MSVC thread-safe statics also use TLS). Check after each build that
the TLS data directory (PE data directory 9) is `(0, 0)`. Exe builds before 2026-10-27 had the older dll without TLS.

## Speed (what was done, all bit-identical)
* `vector<vector<double>>` (`yh_`, `wm_`) -> `Mat`, one contiguous block; row loops use hoisted
  `__restrict` pointers (`row_add`, `row_axpy`, ... in `LSODA.cpp`) so they vectorize.
* `vmnorm` with four independent running maxima (max over non-NaN values is order independent).
* BLAS-like kernels (`dgefa`, `dgesl`, `ddot1`, `daxpy1`, ...) take raw pointers.
* `lsoda_wrapper` reuses `LSODA` solvers + work vectors from a pool (free list under an `SRWLOCK`; `reset_state()` puts
  every scalar back to the fresh-object value, a nested call from an rhs callback simply takes another slot). Checked
  bit-identical on interleaved models and with 8 threads in parallel. It was `thread_local` until 2026-11-06, see below.
* `CompassModelsCPP.solve` (Python): float64, C-contiguous, writable arrays go to the dll in place via
  `c_double.from_buffer` (1.7 us per `data_as` pointer before); anything else falls back to the copying path.
* `XRouter.run_model` no longer imports `CompassModelsCPP` inside the timed region.

Per solve on the stored payloads (solver call only; JIT = numba lsoda, same payloads, JIT timings vary 5-15% between runs):

| model | C++ (us) | JIT (us) | C++ / JIT |
|---|---|---|---|
| model_V (LSODA) | ~385-400 | ~440-465 | ~0.85-0.9 |
| model_PK_18 | ~10.3 | ~17-18 | ~0.6 |
| model_PK_19 | ~12-13 | ~19-22 | ~0.6 |
| model_PK_22 | ~6.0 | ~13-19 | ~0.35-0.45 |

The bit-exact x87 `pow` costs `model_V` about 30% (295 -> 385 us before/after) and the PK models 5-10%; it is the price of
identical numbers. `model_V` with `set_exact_v(1)` takes ~60 us but is not bit-identical.

## Workflow when touching the C++ again
```
python _internal/tools/bench_cpp_models.py --jit --save data/integrity/jit_ref.npz   # outputs of the numba reference
(edit sources, run build.bat)
python _internal/tools/bench_cpp_models.py --cmp data/integrity/jit_ref.npz           # must print BIT-IDENTICAL for all 4 models
python _internal/tools/bench_cpp_models.py                                            # timing of the dll
python _internal/tools/bench_cpp_models.py --jit                                      # timing of the numba lsoda
```
Needs the project venv and the real `data/integrity/compass_metrics.db`. Restart the app afterwards (the dll is loaded once
per process). To re-check end to end, replay the stored `safe_space_calc` Perfect IO payloads with `USE_PRECOMPILED_MODELS=0`
and `=2` (IOCompare and Timing stubbed so nothing is written) and compare against `expected_json`; both must give 0 differences.

## Things measured that did NOT help (do not retry)
`/GL`, `/Ob3`, `/Oi`, `restrict` on the model functions, SSE2 `vmnorm` intrinsics, splitting the `1/ewt` loop, AVX/AVX2/fast-math,
PGO, `cbrt` instead of `pow`, DOPRI5 for the PK models (10-19% of payloads leave tolerance), caching repeated payloads (~1%
repeats). Linking the dll with `/MD` does not change the results by itself (the `pow` of LSODA was the main cause).
Clang bridge (`USE_PRECOMPILED_MODELS=1`) is ~6 us/call slower because `XRouter.get_model` redefines a class on every call.
