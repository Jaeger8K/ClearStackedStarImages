from tkinter import messagebox
from astrostakos import run


def run_astrostakos():
    try:
        output_path = run()

        if not output_path:
            return  # user cancelled

        messagebox.showinfo(
            "AstroStakos finished",
            f"Output saved to:\n{output_path}"
        )

    except Exception as e:
        messagebox.showerror("AstroStakos error", str(e))