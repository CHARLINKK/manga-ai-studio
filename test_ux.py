import customtkinter as ctk

class CTkToast(ctk.CTkFrame):
    def __init__(self, master, message, duration=3000, **kwargs):
        super().__init__(master, fg_color=("#333", "#222"), corner_radius=8, **kwargs)
        self.message = message
        self.duration = duration
        
        self.lbl = ctk.CTkLabel(self, text=self.message, text_color="white", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl.pack(padx=20, pady=10)
        
        self.place(relx=0.5, rely=0.9, anchor="center")
        self.lift() # Bring to front
        self.after(self.duration, self.destroy)

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.schedule_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self._id = None

    def schedule_tooltip(self, event=None):
        self._id = self.widget.after(500, self.show_tooltip)

    def show_tooltip(self):
        if self.tooltip:
            return
        # Use winfo_rootx instead of bbox to avoid exceptions on Frames/Labels!
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tooltip = ctk.CTkToplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        self.tooltip.attributes("-topmost", True)
        
        frame = ctk.CTkFrame(self.tooltip, fg_color=("#333", "#222"), corner_radius=5)
        frame.pack(fill="both", expand=True)
        label = ctk.CTkLabel(frame, text=self.text, text_color="white", justify="left", font=ctk.CTkFont(size=12))
        label.pack(padx=10, pady=5)

    def hide_tooltip(self, event=None):
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

app = ctk.CTk()
app.geometry("400x300")

tv = ctk.CTkTabview(app)
tv.pack(fill="both", expand=True)
t1 = tv.add("Tab 1")

btn = ctk.CTkButton(t1, text="Show Toast", command=lambda: CTkToast(app, "Hello Toast!"))
btn.pack(pady=20)
ToolTip(btn, "This is a tooltip without bbox error!")

app.mainloop()
