# Benchmarks - Ray Tracer

## Environment

- Running On: MacBook Air (M2) - 8 cores (4 performance + 4 efficiency), 8 GB RAM
- macOS [version - 26.5.2], Apple clang [version - 21]

## Standard Render Workload

Final scene (about 485 spheres, materials vary), 1200x675, 100 spp, max depth: 50

## Raw Log

| Date       | Commit Hash   | Build         | Threads| spp | Time(s)   | Notes                       |
|------------|---------------|---------------|-------:|----:|----------:|-----------------------------|
| 2026-08-04 |   25cc2eb     | Release (-O3) |      1 | 100 |  188.74   | baseline                    |
| 2026-08-05 |   25cc2eb     | Debug (-O0). |      1 | 100 |  4117.27  | baseline                    |
| 2026-08-08 |   103a64f     | Release (-O3) |      1 | 100 |  322.20   | framebuffer (on battery — excluded from analysis) |
| 2026-08-08 |   103a64f     | Release (-O3) |      1 | 100 |  187.93   |  framebuffer addition       |
| 2026-08-09 |   4d5734f     | Release (-O3) |      1 | 100 |  190.38   | RNG thread-safe addition (new baseline)   |
| 2026-08-08 |   af5a5ad     | Release (-O3) |      1 | 100 |  186.45   |  RNG fully thread safe (urd was not thread local for previous run)       |
| 2026-10-09 |   b2882e3     | Release (-O3) |      1 | 100 |  189.35   | Multithreaded code ran with only one thread |
| 2026-10-09 |   b2882e3     | Release (-O3) |      8 | 100 |  47.49    | First multithreaded run with 8 threads |
| 2026-10-09 |   1e91eb7     | Release (-O3) |      8 | 500 |  240.13   | Hero render with 8 thread run on spp set to 500, uncommitted  |

## Experiments

### 1 - Compiler optimization (denominator as -O0 Running 1 thread)

| Build   | Time (s) | Speedup |
|---------|---------:|--------:|
| -O0     |  4117.27 |   1.00x |
| -O3     |   188.74 |   21.8x |

### 2 - Thread scaling (denominator as -O3 Release, Running 1 Thread)

| Threads | Best of 3 (s)  | Speedup |
|---------|----------------|---------|
| 1 | 189.12 | 1.00x |
| 2 | 97.97 | 1.93x |
| 4 | 55.27 | 3.42x |
| 8 | 46.52 | 4.07x |
| 16 | 46.75 | 4.05x |

Serial fraction (write/total), 1 thread: 0.10%
Amdahl limit on 8 identical cores: 7.95x
4 threads: 3.42x = 86% of perfect (Performance-cores only)
Threads 5-8 added 0.64×  ->  one Efficiency-core = about 0.20 of 1 P-core