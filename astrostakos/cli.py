from .io import select_input_file
from .pipeline import run


def main():
    path = select_input_file()
    out = run(path)
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
