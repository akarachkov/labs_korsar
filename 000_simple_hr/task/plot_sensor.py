"""Построение временных рядов d1 и d2 из файла _sensor_1.dat.

Зависимости: python -m pip install pandas matplotlib
Запуск: python plot_sensor.py
Без окна: python plot_sensor.py --no-show
"""

import argparse
from pathlib import Path

import pandas as pd


def main():
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "file", nargs="?", type=Path,
        default=script_dir.parent / "result" / "out" / "_sensor_1.dat",
        help="Путь к исходному файлу (по умолчанию относительно скрипта).",
    )
    parser.add_argument(
        "--output", type=Path,
        help="Путь для сохранения графиков (по умолчанию sensor_1.png рядом с данными).",
    )
    parser.add_argument("--no-show", action="store_true", help="Не открывать окно графиков.")
    args = parser.parse_args()
    if args.output is None:
        args.output = args.file.resolve().parent / "sensor_1.png"

    if args.no_show:
        import matplotlib
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        data = pd.read_csv(args.file, sep=r"\s+", encoding="utf-8-sig")
        required = {"TAU", "d1", "d2"}
        if not required.issubset(data.columns):
            raise ValueError("В заголовке файла должны быть столбцы TAU, d1 и d2.")
        if data.empty:
            raise ValueError("Файл не содержит данных.")
        data[["TAU", "d1", "d2"]] = data[["TAU", "d1", "d2"]].apply(pd.to_numeric, errors="raise")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(10, 7), constrained_layout=True)
    for ax, name, title, color in zip(
        axes, ("d1", "d2"), ("Расход, кг/с", "Давление, МПа"), ("tab:blue", "tab:orange")
    ):
        ax.plot(data["TAU"], data[name], color=color, linewidth=1.5)
        ax.set_title(title)
        ax.set_ylabel(title)
        ax.grid(True, alpha=0.3)
    axes[-1].set_xlabel("TAU")
    fig.suptitle(args.file.name)
    fig.savefig(args.output, dpi=180)
    print(f"Графики сохранены: {args.output.resolve()}")
    if not args.no_show:
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
