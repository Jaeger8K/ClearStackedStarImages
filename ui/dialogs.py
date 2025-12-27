import threading
import tkinter as tk
from tkinter import messagebox, ttk
from astrostakos import run
from astrostakos.io import select_input_file


def run_astrostakos():
    try:
        # Choose file on main thread (file dialogs must run on main GUI thread)
        input_path = select_input_file()
        if not input_path:
            return  # user cancelled file selection

        # Build progress dialog
        root = tk._default_root
        progress_win = tk.Toplevel(root)
        progress_win.title("Running AstroStakos")
        progress_win.resizable(False, False)
        progress_win.geometry("420x120")

        label = ttk.Label(progress_win, text="Starting...")
        label.pack(padx=10, pady=(10, 6))

        pb = ttk.Progressbar(progress_win, orient='horizontal', mode='determinate', length=380)
        pb.pack(padx=10, pady=(0, 10))

        cancel_event = threading.Event()

        def on_cancel():
            cancel_event.set()
            label.config(text="Cancelling...")

        btn = ttk.Button(progress_win, text="Cancel", command=on_cancel)
        btn.pack(pady=(0, 10))

        result = {'path': None, 'error': None}

        # Thread-safe callback: called from worker thread
        def progress_callback(fraction, message=None):
            # Schedule GUI update on main thread
            percent = int(fraction * 100)
            def ui_update():
                pb['value'] = percent
                label.config(text=message or f"{percent}%")
            progress_win.after(0, ui_update)
            # Returning False signals cancellation
            return not cancel_event.is_set()

        def worker():
            try:
                out = run(input_file=input_path, on_progress=progress_callback)
                result['path'] = out
            except Exception as e:
                result['error'] = e
            finally:
                # Close progress dialog from main thread
                progress_win.after(0, progress_win.destroy)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        # make modal
        progress_win.transient(root)
        progress_win.grab_set()
        progress_win.wait_window()

        if result['error']:
            if isinstance(result['error'], RuntimeError) and str(result['error']) == 'Cancelled':
                messagebox.showinfo("AstroStakos", "Operation cancelled")
                return
            messagebox.showerror("AstroStakos error", str(result['error']))
            return

        output_path = result['path']
        if output_path:
            messagebox.showinfo("AstroStakos finished", f"Output saved to:\n{output_path}")

    except Exception as e:
        messagebox.showerror("AstroStakos error", str(e))