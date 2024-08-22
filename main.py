import tkinter as tk
from tkinter import filedialog, messagebox
import os

def filter_log(input_file, output_file, param):
    try:
        with open(input_file, 'r') as log_in:
            with open(output_file, 'w') as log_out:
                for line in log_in:
                    if param in line:
                        log_out.write(line)
        messagebox.showinfo("Completed", f"Filtering completed. The new file has been saved as '{output_file}'.")
    except FileNotFoundError:
        messagebox.showerror("Error", f"The file '{input_file}' was not found.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def select_file():
    input_file = filedialog.askopenfilename(
        title="Select the log file",
        filetypes=(("Log Files", "*.log"), ("All Files", "*.*"))
    )
    if input_file:
        label_selected_file_path.config(text=input_file)

def generate_unique_filename(output_file):
    """
    Generates a unique filename by adding a number in parentheses if necessary.
    """
    base, ext = os.path.splitext(output_file)
    i = 1
    unique_file = output_file
    while os.path.exists(unique_file):
        unique_file = f"{base}({i}){ext}"
        i += 1
    return unique_file

def execute_filter():
    input_file = label_selected_file_path.cget("text")
    param = entry_param.get()
    output_file = os.path.join(os.path.dirname(input_file), f"filtered_{os.path.basename(input_file)}")

    if not input_file or not param:
        messagebox.showwarning("Warning", "All fields must be filled!")
    else:
        output_file = generate_unique_filename(output_file)
        filter_log(input_file, output_file, param)

def close_app():
    # Closes the command prompt
    if 'PYTHON_CWD' in os.environ:
        os.system('taskkill /PID %d /F' % os.getpid())
    root.destroy()

# Main interface configuration
root = tk.Tk()
root.title("Log Filter Tool")

# Event to close the interface
root.protocol("WM_DELETE_WINDOW", close_app)

# "Select File" button
btn_select_file = tk.Button(root, text="Select File", command=select_file)
btn_select_file.pack(padx=10, pady=5)

# "File Path" label
label_file_path = tk.Label(root, text="File Path:")
label_file_path.pack(pady=5)

# Label to display the selected file path
label_selected_file_path = tk.Label(root, text="No file selected", fg="blue", wraplength=400)
label_selected_file_path.pack(pady=5)

# "Enter the parameter to filter by:" label
label_param = tk.Label(root, text="Enter the parameter to filter by (case sensitive):")
label_param.pack(pady=5)

# Entry field for the filtering parameter
entry_param = tk.Entry(root, width=50)
entry_param.pack(pady=5)

# "Generate Log" button
btn_generate_log = tk.Button(root, text="Generate Log", command=execute_filter)
btn_generate_log.pack(pady=20)

root.mainloop()