import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk
from document import ChineseDocumentProcessor
from gui import ScrollableCanvas, StepsList, SettingsPanel
from config import ConfigManager

class ProcessorGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Chinese Document Processor")
        self.processor = ChineseDocumentProcessor()
        self.config_manager = ConfigManager()

        self.image = None
        self.processed_image = None
        self.intermediate_results = {}
        self.current_step_index = 0

        self.setup_styles()
        self.create_widgets()

        self.master.bind('<Left>', self.show_previous_step)
        self.master.bind('<Right>', self.show_next_step)
        self.master.bind("<Configure>", self.on_window_resize)

    def setup_styles(self):
        style = ttk.Style()
        style.configure('Left.TFrame', background='#e6e6e6')
        style.configure('Right.TFrame', background='#d9d9d9')
        style.configure('TButton', font=('Arial', 12))
        style.configure('TLabel', font=('Arial', 11))
        style.configure('TLabelframe', font=('Arial', 12, 'bold'))

    def create_widgets(self):
        self.master.geometry("1200x800")
        self.master.configure(bg='#f0f0f0')

        # Left panel for image display
        self.left_panel = ttk.Frame(self.master, style='Left.TFrame')
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollable_canvas = ScrollableCanvas(self.left_panel)
        self.scrollable_canvas.pack(fill=tk.BOTH, expand=True)

        # Right panel for controls
        self.right_panel = ttk.Frame(self.master, style='Right.TFrame')
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=10, pady=10)

        ttk.Button(self.right_panel, text="Load Image", command=self.load_image).pack(pady=10)

        # Notebook for steps and settings
        self.notebook = ttk.Notebook(self.right_panel)
        self.notebook.pack(expand=True, fill=tk.BOTH)

        # Steps tab
        self.steps_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.steps_tab, text="Steps")

        self.steps_list = StepsList(self.steps_tab, list(self.processor.steps.keys()))
        self.steps_list.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        self.steps_list.listbox.bind('<<ListboxSelect>>', self.update_steps)

        ttk.Button(self.steps_tab, text="Move Up", command=self.move_step_up).pack(pady=5)
        ttk.Button(self.steps_tab, text="Move Down", command=self.move_step_down).pack(pady=5)

        # Settings tab
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="Settings")

        self.settings_panel = SettingsPanel(self.settings_tab, self.config_manager.get_setting_details())
        self.settings_panel.pack(fill=tk.BOTH, expand=True)

        ttk.Button(self.right_panel, text="Process Image", command=self.process_image).pack(pady=10)
        ttk.Button(self.right_panel, text="Reset to Defaults", command=self.reset_to_defaults).pack(pady=5)

        self.step_label = ttk.Label(self.right_panel, text="")
        self.step_label.pack(pady=5)

        zoom_frame = ttk.Frame(self.right_panel)
        zoom_frame.pack(pady=5)
        ttk.Button(zoom_frame, text="Zoom In", command=self.zoom_in).pack(side=tk.LEFT, padx=5)
        ttk.Button(zoom_frame, text="Zoom Out", command=self.zoom_out).pack(side=tk.LEFT, padx=5)

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff")])
        if file_path:
            self.image = cv2.imread(file_path)
            if self.image is not None:
                self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(self.image)
                self.scrollable_canvas.set_image(pil_image)
            else:
                messagebox.showerror("Error", "Failed to load the image.")

    def process_image(self):
        if self.image is None:
            messagebox.showwarning("Warning", "Please load an image first.")
            return

        selected_steps = self.steps_list.get_selected_steps()
        current_settings = self.settings_panel.get_current_settings()

        self.processed_image, self.intermediate_results = self.processor.process(self.image, selected_steps, current_settings)
        self.current_step_index = 0
        self.display_current_step()

    def display_current_step(self):
        selected_steps = self.steps_list.get_selected_steps()
        if 0 <= self.current_step_index < len(selected_steps):
            current_step = selected_steps[self.current_step_index]
            if current_step in self.intermediate_results:
                pil_image = Image.fromarray(self.intermediate_results[current_step])
                self.scrollable_canvas.set_image(pil_image)
                self.step_label.config(text=f"Step: {current_step}")
            else:
                self.step_label.config(text="No result for this step")
        elif self.current_step_index == len(selected_steps):
            pil_image = Image.fromarray(self.processed_image)
            self.scrollable_canvas.set_image(pil_image)
            self.step_label.config(text="Final Result")

    def update_steps(self, event):
        selected_steps = self.steps_list.get_selected_steps()
        for step in self.processor.steps.keys():
            self.config_manager.update_step(step, step in selected_steps)

    def move_step_up(self):
        self.steps_list.move_step(-1)
        self.update_steps(None)

    def move_step_down(self):
        self.steps_list.move_step(1)
        self.update_steps(None)

    def zoom_in(self):
        self.scrollable_canvas.zoom(1.1)

    def zoom_out(self):
        self.scrollable_canvas.zoom(0.9)

    def show_next_step(self, event):
        selected_steps = self.steps_list.get_selected_steps()
        if self.current_step_index < len(selected_steps):
            self.current_step_index += 1
            self.display_current_step()

    def show_previous_step(self, event):
        if self.current_step_index > 0:
            self.current_step_index -= 1
            self.display_current_step()

    def on_window_resize(self, event):
        self.scrollable_canvas.on_resize(event)

    def reset_to_defaults(self):
        self.config_manager.reset_to_defaults()
        self.settings_panel.load_settings(self.config_manager.get_settings())
        self.steps_list.listbox.selection_clear(0, tk.END)
        messagebox.showinfo("Reset", "Settings have been reset to default values.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ProcessorGUI(root)
    root.mainloop()
