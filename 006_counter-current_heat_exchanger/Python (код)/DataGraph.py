import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # без открытия окна
import matplotlib.pyplot as plt
from datetime import datetime


# ============================================================
# НАСТРОЙКА
# ============================================================
filepath = r"C:\Users\Toy_G\Desktop\ВУЗ\6 курс 1 семестр\Инновационные подходы в проектировании и конструировании реакторов АЭС\Лабораторная работа 1\labs_korsar-master\labs_korsar-master\006_counter-current_heat_exchanger\КОРСАР (код)\\result.dat"
N1 = 10                # число ячеек по длине (как в kordat)
L_total = 3.0          # полная длина теплообменника, м (Lt из kordat)
STATIONARY_TOL = 0.01  # порог "стационарности" по T, К


# ============================================================
# 1. ЗАГРУЗКА ДАННЫХ
# ============================================================

def load_data(filepath, n1):
    """
    Чтение result.dat, полученного утилитой KUTIL2.
    KUTIL2 может разбивать одну временную запись на несколько строк,
    поэтому собираем ВСЕ числа подряд и нарезаем по (1 + 6*N1).
    """
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    tokens = text.replace(',', ' ').split()
    numbers = []
    for tok in tokens:
        try:
            numbers.append(float(tok))
        except ValueError:
            continue

    n_per_row = 1 + 6 * n1
    n_rows = len(numbers) // n_per_row
    if n_rows == 0:
        raise RuntimeError(
            f"Прочитано {len(numbers)} чисел, "
            f"а для одной записи нужно {n_per_row}. "
            "Проверьте kutdat и kordat."
        )

    used = n_rows * n_per_row
    data = np.array(numbers[:used]).reshape(n_rows, n_per_row)
    print(f"  Прочитано чисел: {len(numbers)}, "
          f"полных записей: {n_rows}, "
          f"в записи: {n_per_row} столбцов")

    time = data[:, 0]
    T_hot   = data[:, 1           : 1 + N1]
    T_cold  = data[:, 1 + N1      : 1 + 2 * N1]
    Tw_in   = data[:, 1 + 2 * N1  : 1 + 3 * N1]
    Tw_out  = data[:, 1 + 3 * N1  : 1 + 4 * N1]
    ALW_in  = data[:, 1 + 4 * N1  : 1 + 5 * N1]
    ALW_out = data[:, 1 + 5 * N1  : 1 + 6 * N1]

    return {
        'time': time,
        'T_hot': T_hot,
        'T_cold': T_cold,
        'Tw_in': Tw_in,
        'Tw_out': Tw_out,
        'ALW_in': ALW_in,
        'ALW_out': ALW_out,
    }


# ============================================================
# 2. ОПРЕДЕЛЕНИЕ ИНДЕКСА "СТАЦИОНАРНОГО" СРЕЗА
# ============================================================

def find_stationary_index(data, tol=STATIONARY_TOL):
    """
    Возвращает индекс временного слоя, который считаем стационарным.
    Алгоритм: идём с конца и ищем последний слой, который отличается
    от предыдущего меньше, чем на tol по всем T (потоки + стенки).
    Если такого нет — возвращаем последний индекс и предупреждаем.
    """
    stack = np.hstack([
        data['T_hot'], data['T_cold'],
        data['Tw_in'], data['Tw_out'],
    ])   # (n_times, 4*N1)
    n = stack.shape[0]
    for i in range(n - 1, 0, -1):
        diff = np.max(np.abs(stack[i] - stack[i - 1]))
        if diff < tol:
            print(f"  Стационарный срез: индекс {i}, t = {data['time'][i]:.3f} с "
                  f"(макс. ΔT между соседними слоями = {diff:.4g} К)")
            return i
    print(f"  ⚠ Стационар не достигнут: берём последний срез "
          f"t = {data['time'][-1]:.3f} с. Рекомендуется увеличить fin_tim.")
    return n - 1


# ============================================================
# 3. ГРАФИК 1: ТЕМПЕРАТУРЫ ПОТОКОВ И СТЕНКИ (стационар)
# ============================================================

def plot_steady_temperature(data, idx_stat, L_total, save_dir):
    x = np.linspace(0, L_total, N1)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x, data['T_hot'][idx_stat],   '-',  lw=2.0, label='Горячий поток (T_hot)')
    ax.plot(x, data['T_cold'][idx_stat],  '-',  lw=2.0, label='Холодный поток (T_cold)')
    ax.plot(x, data['Tw_in'][idx_stat],   '--', lw=1.6, label='Стенка, внутр. поверхность (Tw1)')
    ax.plot(x, data['Tw_out'][idx_stat],  '--', lw=1.6, label='Стенка, наружн. поверхность (Tw2)')

    ax.set_xlabel('Координата вдоль теплообменника, м')
    ax.set_ylabel('Температура, К')
    ax.set_title(f'Температуры потоков и стенки (стационар, t = {data["time"][idx_stat]:.2f} с)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    fig.savefig(os.path.join(save_dir, '01_steady_temperature.png'), dpi=150)
    plt.close(fig)
    print("  Сохранён график: 01_steady_temperature.png")


# ============================================================
# 4. ГРАФИК 2: КОЭФФИЦИЕНТЫ ТЕПЛООТДАЧИ (стационар)
# ============================================================

def plot_steady_alpha(data, idx_stat, L_total, save_dir):
    x = np.linspace(0, L_total, N1)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x, data['ALW_in'][idx_stat],  '-',  lw=2.0,
            label=r'$\alpha$ внутр. поверхности (ALW1)')
    ax.plot(x, data['ALW_out'][idx_stat], '--', lw=2.0,
            label=r'$\alpha$ наружн. поверхности (ALW2)')

    ax.set_xlabel('Координата вдоль теплообменника, м')
    ax.set_ylabel(r'$\alpha$, Вт/(м$^2\cdot$К)')
    ax.set_title(f'Коэффициенты теплоотдачи (стационар, t = {data["time"][idx_stat]:.2f} с)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    fig.savefig(os.path.join(save_dir, '02_steady_alpha.png'), dpi=150)
    plt.close(fig)
    print("  Сохранён график: 02_steady_alpha.png")


# ============================================================
# 5. ГРАФИК 3: ТЕМПЕРАТУРЫ НА ВЫХОДЕ ВО ВРЕМЕНИ
# ============================================================

def plot_outlet_temperature(data, save_dir):
    """
    Изменение температуры потоков во времени на ВЫХОДЕ из каналов.

    Схема потоков (из kordat):
      - CH1 (горячий) идёт СПРАВА НАЛЕВО:
            подача массы в ячейку N1, уход через ячейку 1
            => выход = ячейка 1 (индекс 0)
      - CH2 (холодный) идёт СЛЕВА НАПРАВО:
            подача массы в ячейку 1, уход через ячейку N1
            => выход = ячейка N1 (индекс N1-1)
    """
    i_out_hot  = 0         # выход горячего канала — ячейка 1
    i_out_cold = N1 - 1    # выход холодного канала — ячейка N1

    t = data['time']
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(t, data['T_hot'][:, i_out_hot],   '-',  lw=2.0,
            label='Горячий поток на выходе (ячейка 1)')
    ax.plot(t, data['T_cold'][:, i_out_cold], '-',  lw=2.0,
            label='Холодный поток на выходе (ячейка N1)')

    ax.set_xlabel('Время, с')
    ax.set_ylabel('Температура, К')
    ax.set_title('Изменение температур потоков на выходе во времени')
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    fig.savefig(os.path.join(save_dir, '03_outlet_temperature_vs_time.png'), dpi=150)
    plt.close(fig)
    print("  Сохранён график: 03_outlet_temperature_vs_time.png")


# ============================================================
# 6. ГРАФИК 4: КОЭФФИЦИЕНТЫ ТЕПЛООТДАЧИ В ЦЕНТРЕ ВО ВРЕМЕНИ
# ============================================================

def plot_center_alpha(data, save_dir):
    """
    Изменение коэффициента теплоотдачи во времени в ЦЕНТРЕ каналов.
    Центр — ячейка с индексом N1//2.
    """
    i_mid = N1 // 2
    t = data['time']

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(t, data['ALW_in'][:, i_mid],  '-',  lw=2.0,
            label=r'$\alpha$ внутр. поверхности (в центре)')
    ax.plot(t, data['ALW_out'][:, i_mid], '--', lw=2.0,
            label=r'$\alpha$ наружн. поверхности (в центре)')

    ax.set_xlabel('Время, с')
    ax.set_ylabel(r'$\alpha$, Вт/(м$^2\cdot$К)')
    ax.set_title('Изменение коэффициентов теплоотдачи в центре каналов во времени')
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    fig.savefig(os.path.join(save_dir, '04_center_alpha_vs_time.png'), dpi=150)
    plt.close(fig)
    print("  Сохранён график: 04_center_alpha_vs_time.png")


# ============================================================
# 7. ОСНОВНАЯ ПРОГРАММА
# ============================================================

def main():
    if not os.path.exists(filepath):
        print(f"ОШИБКА: файл не найден:\n  {filepath}")
        return

    abs_path = os.path.abspath(filepath)
    print(f"Используется файл: {abs_path}")

    results_dir = os.path.join(os.path.dirname(abs_path), 'results')
    os.makedirs(results_dir, exist_ok=True)
    print(f"Папка для результатов: {results_dir}")

    data = load_data(abs_path, N1)
    print(f"Время: от {data['time'][0]:.3f} до {data['time'][-1]:.3f} с")

    # ---- Определяем индекс "стационарного" среза ----
    idx_stat = find_stationary_index(data, tol=STATIONARY_TOL)

    # ---- График 1: температуры потоков и стенки в стационаре ----
    print("\nСтрою график 1: температуры потоков и стенки (стационар)...")
    plot_steady_temperature(data, idx_stat, L_total, results_dir)

    # ---- График 2: коэффициенты теплоотдачи в стационаре ----
    print("\nСтрою график 2: коэффициенты теплоотдачи (стационар)...")
    plot_steady_alpha(data, idx_stat, L_total, results_dir)

    # ---- График 3: температуры на выходе во времени ----
    print("\nСтрою график 3: температуры на выходе во времени...")
    plot_outlet_temperature(data, results_dir)

    # ---- График 4: коэффициенты теплоотдачи в центре во времени ----
    print("\nСтрою график 4: коэффициенты теплоотдачи в центре во времени...")
    plot_center_alpha(data, results_dir)

    print("\nГотово. Все графики в папке:")
    print(f"  {results_dir}")


if __name__ == "__main__":
    main()