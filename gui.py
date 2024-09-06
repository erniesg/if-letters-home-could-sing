import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

class ScrollableCanvas(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=1, highlightbackground="gray")
        self.h_scrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.v_scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)

        self.canvas.configure(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.image = None
        self.photo = None
        self.image_id = None
        self.zoom_factor = 1.0

        self.canvas.bind("<Configure>", self.on_resize)

    def set_image(self, image):
        self.image = image
        self.fit_to_width()

    def fit_to_width(self):
        if self.image:
            canvas_width = self.canvas.winfo_width()
            image_width = self.image.width
            self.zoom_factor = canvas_width / image_width
            self.update_image()

    def update_image(self):
        if self.image:
            new_width = int(self.image.width * self.zoom_factor)
            new_height = int(self.image.height * self.zoom_factor)
            resized_image = self.image.copy()
            resized_image = resized_image.resize((new_width, new_height), Image.LANCZOS)
            self.photo = ImageTk.PhotoImage(resized_image)

            if self.image_id:
                self.canvas.delete(self.image_id)

            self.image_id = self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_resize(self, event):
        self.fit_to_width()

    def zoom(self, factor):
        self.zoom_factor *= factor
        self.update_image()

class StepsList(ttk.Frame):
    def __init__(self, master, steps, **kwargs):
        super().__init__(master, **kwargs)
        self.steps_var = tk.StringVar(value=tuple(steps))
        self.listbox = tk.Listbox(self, listvariable=self.steps_var, selectmode=tk.MULTIPLE, bg='white')
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.listbox.yview)

        self.listbox.config(yscrollcommand=self.scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def get_selected_steps(self):
        return [self.listbox.get(i) for i in self.listbox.curselection()]

    def move_step(self, direction):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            return

        new_index = selected_indices[0] + direction
        if 0 <= new_index < self.listbox.size():
            text = self.listbox.get(selected_indices[0])
            self.listbox.delete(selected_indices[0])
            self.listbox.insert(new_index, text)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(new_index)

class SettingsPanel(ttk.Frame):
    def __init__(self, master, settings_info, **kwargs):
        super().__init__(master, **kwargs)
        self.settings = {}
        self.create_settings_widgets(settings_info)

    def create_settings_widgets(self, settings_info):
        for step, step_settings in settings_info.items():
            step_frame = ttk.LabelFrame(self, text=step)
            step_frame.pack(pady=5, padx=10, fill=tk.X)

            self.settings[step] = {}
            for setting, details in step_settings.items():
                label = ttk.Label(step_frame, text=setting)
                label.pack(side=tk.LEFT, padx=5)

                if details['type'] == 'int':
                    var = tk.IntVar(value=details['value'])
                    widget = ttk.Spinbox(step_frame, from_=details['range'][0], to=details['range'][1], textvariable=var)
                elif details['type'] == 'float':
                    var = tk.DoubleVar(value=details['value'])
                    widget = ttk.Spinbox(step_frame, from_=details['range'][0], to=details['range'][1], increment=0.1, textvariable=var)

                widget.pack(side=tk.LEFT, padx=5)
                self.settings[step][setting] = var

    def get_current_settings(self):
        return {step: {k: v.get() for k, v in settings.items()} for step, settings in self.settings.items()}

    def load_settings(self, settings):
        for step, step_settings in settings.items():
            if step in self.settings:
                for setting, value in step_settings.items():
                    if setting in self.settings[step]:
                        self.settings[step][setting].set(value)
