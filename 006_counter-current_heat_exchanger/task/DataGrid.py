import re
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ============================================================
# НАСТРОЙКА
# ============================================================
BASE_DIR = Path(r"C:\Users\Toy_G\Desktop\ВУЗ\6 курс 1 семестр\Инновационные подходы в проектировании и конструировании реакторов АЭС\Лабораторная работа 1\labs_korsar-master\labs_korsar-master\006_counter-current_heat_exchanger\task")
GRID_DIR = BASE_DIR / "Grid"      # Grid/ — внутри task/
PIC_DIR = BASE_DIR.parent / "pic" # pic/ — на уровень выше task/, т.е. в корне 006_counter-current_heat_exchanger/

G_HOT = 1.0     # кг/с, из kordat (Gh)
G_COLD = 1.0    # кг/с, из kordat (Gc)
CP = 4180.0     # Дж/(кг·К), оценка для воды
T0_C = 273.15


# ============================================================
# ЧТЕНИЕ ФАЙЛА И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def collect_files(grid_dir, prefix):
    """
    Возвращает словарь {число: путь} для файлов вида <prefix>N10.dat,
    <prefix>N20.dat, ...
    """
    result = {}
    # Ищем файлы по маске, например resultsN10.dat
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)\.dat$", re.IGNORECASE)
    for p in grid_dir.iterdir():
        if not p.is_file():
            continue
        m = pattern.match(p.name)
        if m:
            key = int(m.group(1))
            result[key] = p
    return dict(sorted(result.items()))


def read_last(path, N):
    """Читает последний временной срез из result.dat, полученного KUTIL2."""
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    numbers = []
    for tok in text.replace(',', ' ').split():
        try:
            numbers.append(float(tok))
        except ValueError:
            continue
    n_cols = 1 + 6 * N
    n_steps = len(numbers) // n_cols
    if n_steps == 0:
        raise ValueError(f"Файл {path} пустой или формат не совпадает (N={N}).")
    return np.array(numbers[:n_steps * n_cols]).reshape(n_steps, n_cols)[-1]


def parse_last(last, N):
    """Разбивает последний срез на группы параметров."""
    T_hot   = last[1           : 1 + N]       - T0_C
    T_cold  = last[1 + N       : 1 + 2*N]     - T0_C
    Tw_in   = last[1 + 2*N     : 1 + 3*N]     - T0_C
    Tw_out  = last[1 + 3*N     : 1 + 4*N]     - T0_C
    ALW_in  = last[1 + 4*N     : 1 + 5*N]
    ALW_out = last[1 + 5*N     : 1 + 6*N]
    return T_hot, T_cold, Tw_in, Tw_out, ALW_in, ALW_out


def compute_Q(T_hot, T_cold, N, G_hot, G_cold, cp):
    """Тепловая мощность по последнему срезу с учётом направлений потоков."""
    T_h_in  = T_hot[N-1]
    T_h_out = T_hot[0]
    T_c_in  = T_cold[0]
    T_c_out = T_cold[N-1]
    Q_hot  = G_hot  * cp * (T_h_in  - T_h_out)
    Q_cold = G_cold * cp * (T_c_out - T_c_in)
    return {
        'T_h_in': T_h_in, 'T_h_out': T_h_out,
        'T_c_in': T_c_in, 'T_c_out': T_c_out,
        'Q_hot': Q_hot, 'Q_cold': Q_cold,
        'Q': 0.5 * (Q_hot + Q_cold),
    }


def gci(f1, f2, f3, r, label=""):
    """GCI Роуча. f1, f2, f3 — значения на грубой, средней и мелкой сетках."""
    eps21 = f2 - f1
    eps32 = f3 - f2
    if abs(eps32) < 1e-15 or abs(eps21) < 1e-15:
        print(f"{label}: p не определён (нулевая разница)")
        return
    p = abs(np.log(abs(eps32 / eps21)) / np.log(r))
    f_ext = f3 + (f3 - f2) / (r**p - 1)
    e_ext = abs((f_ext - f3) / f_ext)
    gci_fine = 1.25 * e_ext / (r**p - 1) * 100
    print(f"{label}: p={p:.3f}, f_ext={f_ext:.4f}, GCI_fine={gci_fine:.3f}%")


# ============================================================
# ЧАСТЬ 1: СХОДИМОСТЬ ПО ДЛИНЕ (N)
# ============================================================

def study_N():
    files = collect_files(GRID_DIR, "resultsN")
    if not files:
        print(f"В папке {GRID_DIR} нет файлов resultsN*.dat")
        return {}

    Ns_all = list(files.keys())
    results_N = {}
    print("=== СХОДИМОСТЬ ПО ДЛИНЕ (N) ===")
    for N, path in files.items():
        last = read_last(path, N)
        T_hot, T_cold, *_ = parse_last(last, N)
        res = compute_Q(T_hot, T_cold, N, G_HOT, G_COLD, CP)
        results_N[N] = res
        print(f"N={N:3d}  T_h.out={res['T_h_out']:8.4f} °C  "
              f"T_c.out={res['T_c_out']:8.4f} °C  "
              f"Q={res['Q']/1000:9.4f} кВт")

    # Отклонения от самой грубой сетки
    N0 = Ns_all[0]
    Q0  = results_N[N0]['Q']
    Th0 = results_N[N0]['T_h_out']
    Tc0 = results_N[N0]['T_c_out']

    Q_rel  = [abs(results_N[N]['Q']       - Q0)  / abs(Q0)  * 100 for N in Ns_all]
    Th_rel = [abs(results_N[N]['T_h_out'] - Th0) / abs(Th0) * 100 for N in Ns_all]
    Tc_rel = [abs(results_N[N]['T_c_out'] - Tc0) / abs(Tc0) * 100 for N in Ns_all]

    plt.figure(figsize=(10, 6))
    plt.plot(Ns_all, Q_rel,  'r-o', label='Q')
    plt.plot(Ns_all, Th_rel, 'b-s', label='T_h.out')
    plt.plot(Ns_all, Tc_rel, 'g-^', label='T_c.out')
    
    plt.xlabel('Число ячеек по длине N')
    plt.ylabel(f'Отклонение от N={N0}, %')
    plt.title('Сеточная сходимость по длине')
    
    # Задаем ось X так, чтобы шаг был 5, и она начиналась с 0
    plt.xlim(0, Ns_all[-1] + 5)
    plt.xticks(range(0, Ns_all[-1] + 6, 5))  # Метки 0, 5, 10, 15...
    
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    PIC_DIR.mkdir(exist_ok=True)
    plt.savefig(PIC_DIR / 'convergence_N.png', dpi=150)
    plt.close()
    print(f"  Сохранён график: {GRID_DIR / 'convergence_N.png'}")

    # GCI по последним трём сеткам (если их хотя бы 3)
    if len(Ns_all) >= 3:
        N1_, N2_, N3_ = Ns_all[-3], Ns_all[-2], Ns_all[-1]
        r = (N2_ / N1_ * N3_ / N2_) ** 0.5
        print(f"\n--- GCI по N ({N1_}, {N2_}, {N3_}, r≈{r:.3f}) ---")
        gci(results_N[N1_]['Q'],       results_N[N2_]['Q'],       results_N[N3_]['Q'],       r, "Q")
        gci(results_N[N1_]['T_h_out'], results_N[N2_]['T_h_out'], results_N[N3_]['T_h_out'], r, "T_h.out")
        gci(results_N[N1_]['T_c_out'], results_N[N2_]['T_c_out'], results_N[N3_]['T_c_out'], r, "T_c.out")

    return results_N


# ============================================================
# ЧАСТЬ 2: СХОДИМОСТЬ ПО ТОЛЩИНЕ СТЕНКИ (K)
# ============================================================

def study_K(N_fix):
    files = collect_files(GRID_DIR, "resultsK")
    if not files:
        print(f"\nВ папке {GRID_DIR} нет файлов resultsK*.dat — часть 2 пропущена.")
        return {}

    Ks_all = list(files.keys())
    results_K = {}
    print(f"\n=== СХОДИМОСТЬ ПО K при N={N_fix} ===")
    for K, path in files.items():
        last = read_last(path, N_fix)
        T_hot, T_cold, *_ = parse_last(last, N_fix)
        res = compute_Q(T_hot, T_cold, N_fix, G_HOT, G_COLD, CP)
        results_K[K] = res
        print(f"K={K:3d}  T_h.out={res['T_h_out']:8.4f} °C  "
              f"T_c.out={res['T_c_out']:8.4f} °C  "
              f"Q={res['Q']/1000:9.4f} кВт")

    K0 = Ks_all[0]
    Qk0  = results_K[K0]['Q']
    Thk0 = results_K[K0]['T_h_out']
    Tck0 = results_K[K0]['T_c_out']

    Qk_rel  = [abs(results_K[K]['Q']       - Qk0)  / abs(Qk0)  * 100 for K in Ks_all]
    Thk_rel = [abs(results_K[K]['T_h_out'] - Thk0) / abs(Thk0) * 100 for K in Ks_all]
    Tck_rel = [abs(results_K[K]['T_c_out'] - Tck0) / abs(Tck0) * 100 for K in Ks_all]

    plt.figure(figsize=(10, 6))
    eps = 1e-8 
    plt.semilogy(Ks_all, [val + eps for val in Qk_rel],  'r-o', label='Q')
    plt.semilogy(Ks_all, [val + eps for val in Thk_rel], 'b-s', label='T_h.out')
    plt.semilogy(Ks_all, [val + eps for val in Tck_rel], 'g-^', label='T_c.out')
    
    plt.xlabel('Число узлов по толщине стенки K')
    plt.ylabel(f'|Отклонение от K={K0}| + 1e-8, % (лог. шкала)')
    plt.title(f'Сеточная сходимость по толщине стенки (N={N_fix})')
    
    plt.xticks(Ks_all)
    plt.grid(True, alpha=0.3, which='both')
    plt.legend()
    plt.tight_layout()
    PIC_DIR.mkdir(exist_ok=True)
    plt.savefig(PIC_DIR / 'convergence_K.png', dpi=150)
    plt.close()

    print(f"  Сохранён график: {GRID_DIR / 'convergence_K.png'}")

    if len(Ks_all) >= 3:
        K1_, K2_, K3_ = Ks_all[0], Ks_all[1], Ks_all[2]
        r = (K2_ / K1_ * K3_ / K2_) ** 0.5
        print(f"\n--- GCI по K ({K1_}, {K2_}, {K3_}, r≈{r:.3f}) ---")
        gci(results_K[K1_]['Q'],       results_K[K2_]['Q'],       results_K[K3_]['Q'],       r, "Q")
        gci(results_K[K1_]['T_h_out'], results_K[K2_]['T_h_out'], results_K[K3_]['T_h_out'], r, "T_h.out")
        gci(results_K[K1_]['T_c_out'], results_K[K2_]['T_c_out'], results_K[K3_]['T_c_out'], r, "T_c.out")

    return results_K


# ============================================================
# ОСНОВНАЯ ПРОГРАММА
# ============================================================

if __name__ == "__main__":
    PIC_DIR.mkdir(exist_ok=True)
    GRID_DIR.mkdir(exist_ok=True)
    print(f"Файлы сходимости: {GRID_DIR}")
    print(f"Графики:         {PIC_DIR}\n")

    res_N = study_N()

    if res_N:
        N_fix = max(res_N.keys())   # или задайте вручную, например N_fix = 40
        study_K(N_fix)
    else:
        study_K(N_fix=10)