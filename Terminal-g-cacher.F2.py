# =========================================================================================
# CORE MODULE ENGINE - ARCHITECTURAL DOCUMENTATION & INTERPRETATION MANUAL
# =========================================================================================
#
# --- METROLOGY & SUBSYSTEM DIAGNOSTICS: WHY WE PROBE WHAT WE PROBE ---
#
# 1. PRE-BENCHMARK PROBING MATRIX (THE SYSTEM BASELINE CONTROLS)
#    • Timer Query (time.perf_counter_ns):
#      - Evaluates the raw latency of querying the motherboard's hardware clock (QPC on Win).
#      - If a single query takes > 500 ns, the platform timing source introduces critical noise.
#      - Run 1 vs Run 2 exposes interpreter cold-start caching vs warm JIT-like execution.
#    • String Concat (In-Memory Buffer Allocation):
#      - Measures Python's internal memory manager (PyMalloc) and RAM bandwidth capacity.
#      - Run 1 vs Run 2 exposes heap fragmentation and the efficiency of the Garbage Collector.
#    • Stdout Write (Raw Descriptor Streaming):
#      - Probes the raw throughput of sending un-flushed bytes to the OS pipe buffer layer.
#      - Exposes the immense overhead of C-API boundary crossing and thread locking primitives.
#    • I/O Flush (Kernel-to-Display Sync Barrier):
#      - Measures the time required for the OS kernel to enforce buffer evacuation.
#      - Probes how fast the OS context switches from user space execution to kernel space I/O.
#
# 2. PIVOT REPORT (THE MATRIX PAYLOAD ANALYSIS)
#    • Target Variance (The Precision Metric):
#      - Chronologically tracks how close each 75-frame segment hit the ideal 250.0 ms mark.
#      - Positive variance indicates frame drops (lag); negative indicates time compression.
#    • Thread CPU Load & Busy-Wait Cost (The Resource Equation):
#      - Wall Time (100%) = Thread CPU Load (Active Processing) + Busy-Wait Cost (Idling).
#      - High Busy-Wait (~90%) proves the hardware is idling, waiting for the strict timer gate.
#      - A sudden drop in Busy-Wait correlated with an increase in Thread CPU Load exposes a severe
#        I/O blockage, where the processor must work harder to push bytes through a saturated pipe.
#    • Last Run vs This Run Difference (The Historical Delta):
#      - Persistent XML regression analysis tracking system degradation or cache optimizations.
#      - Increases (red) flag active OS scheduler interference, thermal throttling, or background noise.
#
# =========================================================================================
# FUTURE ARCHITECTURAL FUTURE WORK: FORECASTING POSIX / UNIX BENCHMARK PROFILES
# =========================================================================================
#
# TODO: PORTING LOGIC AND PERFORMANCE EXECUTION CHARACTERISTICS FOR LINUX SUB-ENGINES
#
# 1. PROCESS ALLOCATION & TERMINAL SUBSYSTEM BEHAVIOR (gnome-terminal / xterm)
#    • Windows 11 (Windows Terminal - ConPTY Architecture):
#      - Employs a complex, virtualized DirectX canvas composition wrapper layer.
#      - Windows treats busy loops aggressively via EcoQoS / Thread Director throttling,
#        frequently dropping execution priorities or forcing threads onto slow E-Cores.
#    • Linux POSIX (Native Pseudo-Terminal / PTY / VTE Architecture):
#      - Communicates via highly optimized Unix streams directly mapped into memory pages.
#      - Linux scheduler (CFS / EEVDF) respects busy loops and assigns strict real-time priority.
#
# 2. METRIC COMPARISON EXPECTATIONS FOR EACH TELEMETRY COLUMN (POSIX ENVIRONMENT):
#
#    A. PRE-BENCHMARK MATRIX EXPECTATIONS:
#       • Timer Query:
#         - Linux (clock_gettime with CLOCK_MONOTONIC_RAW) bypasses virtual layer ticks entirely.
#         - Run 1 vs Run 2 will be extremely identical. Avg/Call expected around 15 - 50 ns (3x faster).
#       • String Concat:
#         - Linux glibc allocator (ptmalloc) handles large allocations with native virtual memory maps.
#         - Expect massive performance consistency. Post-GC Run 2 overhead will be near zero.
#       • Stdout Write & I/O Flush:
#         - Linux streams bytes through system VFS descriptors into ring buffers natively.
#         - 5000 iterations will execute up to 5x faster than Win11 due to zero graphics compositor locking.
#
#    B. MAIN BENCHMARK PIVOT REPORT EXPECTATIONS:
#       • Frame Range Range Processing:
#         - Sub-second interval sampling will scale linearly with absolute chronological stability.
#       • Actual Time & Target Variance:
#         - Linux POSIX high-resolution timers will achieve a Target Variance of +/- 0.010 ms max.
#         - The vast, random micro-stutters seen on Windows (e.g., +37 ms lag) will disappear,
#           as Wayland/X11 compositors decouple terminal stdout ingestion from monitor frame rate sync.
#       • Thread CPU Load (The Critical POSIX Divergence):
#         - On Windows, GetProcessTimes fails during busy waiting, reporting a deceptive 0.0% load.
#         - On Linux, resource.getrusage (RUSAGE_SELF) tracks exact hardware clock cycles.
#         - Expected result: Thread CPU Load will report a constant, honest 100.0% for the rendering thread.
#       • Busy-Wait Cost:
#         - Will align with the Windows profile (~90% idling), but with surgical precision.
#         - Sudden drops (I/O choking) will be rare, occurring only under extreme system-wide RAM thrashing.
#       • Last Run vs This Run Difference:
#         - Linux XML comparisons will display absolute structural consistency (variance within nanoseconds).
#         - Background daemons under Linux rarely steal quantum slices from active terminal foreground processes.
#
# =========================================================================================
# END OF TECHNICAL SOURCE DATA PROTOCOL - ARCHITECTURE IS STABLE AND READY FOR DISTRIBUTION
# =========================================================================================

import sys
import math

# Globální rozměry textového terminálu
TERM_COLS = 48
TERM_ROWS = 32

# Reálné rozlišení bitmapy (1 textová buňka = 2x4 sub-pixelů)
MAP_WIDTH = TERM_COLS * 2   # 96
MAP_HEIGHT = TERM_ROWS * 4  # 128

def render_foreground(char, r, g, b):
    """Vytiskne znak. Pozadí zůstává nativně černé, mění se jen barva textu."""
    sys.stdout.write(f"\x1b[38;2;{r};{g};{b}m{char}\x1b[0m")

def get_braille_char(matrix_2x4):
    """Převede matici 2x4 na příslušný Unicode Braille znak zapsaný napevno."""
    # Každá buňka má přesně definované číselné váhy pro bity Unicode standardu
    weights = [[1, 8], [2, 16], [4, 32], [64, 128]]
    char_code = 0
    for row in range(4):
        for col in range(2):
            if matrix_2x4[row][col]:
                char_code |= weights[row][col]
    return chr(0x2800 + char_code)

# --- SIMULACE VSTUPNÍ BITMAPY MAPY (96 x 128 pixelů) ---
bitmap_map = [[0 for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]

# Vertikální cesta středem (tloušťka 2 pixely)
for y in range(MAP_HEIGHT):
    bitmap_map[y][47] = 1
    bitmap_map[y][48] = 1

# Odbočka doprava (rozcestí ve tvaru Y nebo T) ve výšce 60
for x in range(48, MAP_WIDTH):
    # Šikmá cesta nahoru pod úhlem 45°
    target_y = 60 - (x - 48)
    if 0 <= target_y < MAP_HEIGHT:
        bitmap_map[target_y][x] = 1
        bitmap_map[target_y + 1][x] = 1

# --- ENGINE PRO VYKRESLENÍ MAPY SE STMOVÁNÍM ---

print("--- GEOMETRICKÁ MAPA S DETEKCÍ ROZCESTÍ (48x32 buněk) ---")

# Pozice hráče posunutá ke křižovatce, aby byla krásně vidět
PLAYER_X = 48
PLAYER_Y = 75  
MAX_VIDITELNOST = 45.0  # Vzdálenost v pixelech, kde už je absolutní tma

for t_row in range(TERM_ROWS):
    for t_col in range(TERM_COLS):
        
        # Inicializace sub-matice 2x4 čistými nulami
        sub_matrix = [[0, 0], [0, 0], [0, 0], [0, 0]]
        obsahuje_data = False
        pocet_aktivnich_pixelu = 0
        
        for r in range(4):
            for c in range(2):
                pixel_x = t_col * 2 + c
                pixel_y = t_row * 4 + r
                
                # Kontrola přetečení okrajů pole
                if 0 <= pixel_x < MAP_WIDTH and 0 <= pixel_y < MAP_HEIGHT:
                    if bitmap_map[pixel_y][pixel_x] == 1:
                        sub_matrix[r][c] = 1
                        obsahuje_data = True
                        pocet_aktivnich_pixelu += 1
        
        # Výpočet stmívání (vzdálenost středu buňky od pozice hráče)
        cell_center_x = t_col * 2
        cell_center_y = t_row * 4
        dist = math.sqrt((cell_center_x - PLAYER_X)**2 + (cell_center_y - PLAYER_Y)**2)
        
        # Lineární stmívání
        if dist > MAX_VIDITELNOST:
            factor = 0.0
        else:
            factor = 1.0 - (dist / MAX_VIDITELNOST)
            
        gray_val = int(255 * factor)
        
        # Vyhodnocení a vykreslení buňky
        if gray_val < 45 or not obsahuje_data:
            sys.stdout.write(" ")
        else:
            # GEOMETRICKÁ DETEKCE ROZCESTÍ:
            # Pokud se v buňce slévá hlavní cesta i odbočka a jsme v bodě křížení
            if pocet_aktivnich_pixelu >= 5 and (22 <= t_col <= 26) and (13 <= t_row <= 16):
                ascii_znak = "V" if gray_val > 130 else "v"
                render_foreground(ascii_znak, gray_val, gray_val, gray_val)
            else:
                # Standardní cesta přes přesný Braille znak
                braille_char = get_braille_char(sub_matrix)
                if braille_char == chr(0x2800):
                    sys.stdout.write(" ")
                else:
                    render_foreground(braille_char, gray_val, gray_val, gray_val)
                
    sys.stdout.write("\n")  # Konec řádku terminálu
