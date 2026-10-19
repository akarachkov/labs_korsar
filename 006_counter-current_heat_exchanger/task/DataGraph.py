import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


# ============================================================
# НАСТРОЙКА
# ============================================================
filepath = r"C:\Users\Toy_G\Desktop\ВУЗ\6 курс 1 семестр\Инновационные подходы в проектировании и конструировании реакторов АЭС\Лабораторная работа 1\labs_korsar-master\labs_korsar-master\006_counter-current_heat_exchanger\task\\result.dat"
N1 = 10                # число ячеек по длине (как в kordat)
L_total = 3.0          # полная длина теплообменника, м (Lt из kordat)
T0_C = 273.15          # смещение для перевода К -> °C


# ============================================================
# 1. ЗАГРУЗКА ДАННЫХ
# ============================================================

def load_data(filepath, n1):
    """Чтение result.dat, полученного утилитой KUTIL2. KUTIL2 может разбивать одну временную запись на несколько строк, поэтому собираем ВСЕ числа подряд и нарезаем по (1 + 6*N1)."""
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
# 2. ГРАФИК 1: ТЕМПЕРАТУРЫ ПОТОКОВ И СТЕНКИ (последний срез)
# ============================================================

def plot_steady_temperature(data, L_total, save_dir):
    x = np.linspace(0, L_total, N1)
    idx = len(data['time']) - 1   # последний временной слой

    # Перевод в °C
    T_hot_C   = data['T_hot'][idx]  - T0_C
    T_cold_C  = data['T_cold'][idx] - T0_C
    Tw_in_C   = data['Tw_in'][idx]  - T0_C
    Tw_out_C  = data['Tw_out'][idx] - T0_C

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x, T_hot_C,  '-o', color='red',  lw=2.0, ms=5, label='Горячий поток (T_hot)')
    ax.plot(x, T_cold_C, '-o', color='blue', lw=2.0, ms=5, label='Холодный поток (T_cold)')
    ax.plot(x, Tw_in_C,  '--o', color='darkred', lw=1.6, ms=4, label='Стенка, внутр. поверхность (Tw1)')
    ax.plot(x, Tw_out_C, '--o', color='darkblue', lw=1.6, ms=4, label='Стенка, наружн. поверхность (Tw2)')

    ax.set_xlabel('Координата вдоль теплообменника, м')
    ax.set_ylabel('Температура, °C')
    ax.set_title(f'Температуры потоков и стенки (t = {data["time"][idx]:.2f} с)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    fig.savefig(os.path.join(save_dir, '01_steady_temperature.png'), dpi=150)
    plt.close(fig)
    print("  Сохранён график: 01_steady_temperature.png")


# ============================================================
# 3. ГРАФИК 2: КОЭФФИЦИЕНТЫ ТЕПЛООТДАЧИ (последний срез)
# ============================================================

def plot_steady_alpha(data, L_total, save_dir):
    x = np.linspace(0, L_total, N1)
    idx = len(data['time']) - 1

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x, data['ALW_in'][idx],  '-o', color='red',  lw=2.0, ms=5, label=r'$\alpha$ внутр. поверхности (ALW1)')
    ax.plot(x, data['ALW_out'][idx], '-o', color='blue', lw=2.0, ms=5, label=r'$\alpha$ наружн. поверхности (ALW2)')

    ax.set_xlabel('Координата вдоль теплообменника, м')
    ax.set_ylabel(r'$\alpha$, Вт/(м$^2\cdot$К)')
    ax.set_title(f'Коэффициенты теплоотдачи (t = {data["time"][idx]:.2f} с)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    fig.savefig(os.path.join(save_dir, '02_steady_alpha.png'), dpi=150)
    plt.close(fig)
    print("  Сохранён график: 02_steady_alpha.png")


# ============================================================
# 4. ГРАФИК 3: ТЕМПЕРАТУРЫ НА ВЫХОДЕ ВО ВРЕМЕНИ
# ============================================================

def plot_outlet_temperature(data, save_dir):
    """ Схема потоков:
        CH1 (горячий) идёт справа налево: выход = ячейка 1 (индекс 0)
        CH2 (холодный) идёт слева направо: выход = ячейка N1 (индекс N1-1)
    """
    i_out_hot  = 0
    i_out_cold = N1 - 1
    t = data['time']

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(t, data['T_hot'][:, i_out_hot]  - T0_C, '-', color='red',  lw=2.0, label='Горячий поток на выходе (ячейка 1)')
    ax.plot(t, data['T_cold'][:, i_out_cold] - T0_C, '-', color='blue', lw=2.0, label='Холодный поток на выходе (ячейка N1)')

    ax.set_xlabel('Время, с')
    ax.set_ylabel('Температура, °C')
    ax.set_title('Изменение температур потоков на выходе во времени')
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    fig.savefig(os.path.join(save_dir, '03_outlet_temperature_vs_time.png'), dpi=150)
    plt.close(fig)
    print("  Сохранён график: 03_outlet_temperature_vs_time.png")


# ============================================================
# 5. РАСЧЁТ ТЕПЛОВОЙ МОЩНОСТИ
# ============================================================

def compute_performance(data, N1, G_hot, G_cold, cph, cpc):
    """ Расчёт по ПОСЛЕДНЕМУ временному слою. Индексы:
        CH1 (горячий): вход = N1-1, выход = 0
        CH2 (холодный): вход = 0,   выход = N1-1
    """
    idx = len(data['time']) - 1
    i_hot_in,  i_hot_out  = N1-1, 0
    i_cold_in, i_cold_out = 0,   N1-1

    T_hot_in  = data['T_hot'][idx, i_hot_in]
    T_hot_out = data['T_hot'][idx, i_hot_out]
    T_cold_in = data['T_cold'][idx, i_cold_in]
    T_cold_out= data['T_cold'][idx, i_cold_out]

     # Тепловая мощность по горячему и холодному потокам
    Q_hot  = G_hot  * cph * (T_hot_in  - T_hot_out)
    Q_cold = G_cold * cpc * (T_cold_out - T_cold_in)

    # Среднее значение и относительная невязка баланса
    Q = 0.5 * (Q_hot + Q_cold)
    Q_balance_error = abs(Q_hot - Q_cold) / max(abs(Q), 1e-12)

    return {
        'time': data['time'][idx],
        'T_hot_in': T_hot_in, 'T_hot_out': T_hot_out,
        'T_cold_in': T_cold_in, 'T_cold_out': T_cold_out,
        'Q': Q, 'Q_hot': Q_hot, 'Q_cold': Q_cold,
        'Q_balance_error': Q_balance_error,
    }


# ============================================================
# 6. ОСНОВНАЯ ПРОГРАММА
# ============================================================

def main():
    if not os.path.exists(filepath):
        print(f"ОШИБКА: файл не найден:\n  {filepath}")
        return

    abs_path = os.path.abspath(filepath)
    print(f"Используется файл: {abs_path}")

    task_dir = os.path.dirname(abs_path)                 # .../task
    pic_dir  = os.path.join(os.path.dirname(task_dir), 'pic')  # .../pic
    os.makedirs(pic_dir, exist_ok=True)
    results_dir = pic_dir
    print(f"Папка для результатов: {results_dir}")

    data = load_data(abs_path, N1)
    print(f"Время: от {data['time'][0]:.3f} до {data['time'][-1]:.3f} с")

    # ---- График 1: температуры потоков и стенки ----
    print("\nСтрою график 1: температуры потоков и стенки...")
    plot_steady_temperature(data, L_total, results_dir)

    # ---- График 2: коэффициенты теплоотдачи ----
    print("\nСтрою график 2: коэффициенты теплоотдачи...")
    plot_steady_alpha(data, L_total, results_dir)

    # ---- График 3: температуры на выходе во времени ----
    print("\nСтрою график 3: температуры на выходе во времени...")
    plot_outlet_temperature(data, results_dir)

    # ---- Интегральные показатели ----
    perf = compute_performance(data, N1, G_hot=1.0, G_cold=1.0, cph=4180.0, cpc=4180.0)

    # Вывод в консоль
    print("\n" + "="*60)
    print("ТЕПЛОВАЯ МОЩНОСТЬ (последний срез)")
    print("="*60)
    print(f"  Время последнего среза: {perf['time']:.3f} с")
    print(f"  Вход горячего:   {perf['T_hot_in']  - T0_C:.3f} °C")
    print(f"  Выход горячего:  {perf['T_hot_out'] - T0_C:.3f} °C")
    print(f"  Вход холодного:  {perf['T_cold_in'] - T0_C:.3f} °C")
    print(f"  Выход холодного: {perf['T_cold_out']- T0_C:.3f} °C")
    print(f"  Q (по горячему): {perf['Q_hot']:.3f} Вт")
    print(f"  Q (по холодному):{perf['Q_cold']:.3f} Вт")
    print(f"  Q (среднее):     {perf['Q']:.3f} Вт")
    print(f"  Невязка баланса: {perf['Q_balance_error']*100:.4f} %")

    # ---- Сохранение в Q.txt ----
    ntu_path = os.path.join(results_dir, 'Q.txt')
    with open(ntu_path, 'w', encoding='utf-8') as f:
        f.write("ТЕПЛОВАЯ МОЩНОСТЬ (последний срез)\n")
        f.write("=" * 60 + "\n")
        f.write(f"Файл данных: {abs_path}\n")
        f.write(f"Время последнего среза: {perf['time']:.3f} с\n")
        f.write("-" * 60 + "\n")
        f.write(f"Вход горячего:   {perf['T_hot_in']  - T0_C:.3f} °C\n")
        f.write(f"Выход горячего:  {perf['T_hot_out'] - T0_C:.3f} °C\n")
        f.write(f"Вход холодного:  {perf['T_cold_in'] - T0_C:.3f} °C\n")
        f.write(f"Выход холодного: {perf['T_cold_out']- T0_C:.3f} °C\n")
        f.write("-" * 60 + "\n")
        f.write(f"Q (по горячему): {perf['Q_hot']:.3f} Вт\n")
        f.write(f"Q (по холодному):{perf['Q_cold']:.3f} Вт\n")
        f.write(f"Q (среднее):     {perf['Q']:.3f} Вт\n")
        f.write(f"Невязка баланса: {perf['Q_balance_error']*100:.4f} %\n")

    print("\nГотово. Все результаты в папке:")
    print(f"  {results_dir}")


if __name__ == "__main__":
    main()