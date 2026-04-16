import customtkinter as ctk
from scripts.research_studio.features.research import ResearchFrame
from scripts.research_studio.features.linkedin import LinkedInFrame
from scripts.research_studio.features.youtube import YouTubeFrame
from scripts.research_studio.features.insights import InsightsFrame

class ResearchStudio(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI-SEO Research Studio 2024-2026")
        self.geometry("1150x850")

        # Set appearance
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Layout: Sidebar and Main Container
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar Navigation
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar_frame, text="RESEARCH HUB", font=ctk.CTkFont(size=22, weight="bold")).grid(row=0, column=0, padx=20, pady=30)

        self.btn_res = ctk.CTkButton(self.sidebar_frame, text="1. Expert Research", command=lambda: self.show_frame("research"))
        self.btn_res.grid(row=1, column=0, padx=20, pady=10)

        self.btn_li = ctk.CTkButton(self.sidebar_frame, text="2. LinkedIn Scraper", command=lambda: self.show_frame("linkedin"))
        self.btn_li.grid(row=2, column=0, padx=20, pady=10)

        self.btn_yt = ctk.CTkButton(self.sidebar_frame, text="3. YT Transcriber", command=lambda: self.show_frame("youtube"))
        self.btn_yt.grid(row=3, column=0, padx=20, pady=10)

        self.btn_in = ctk.CTkButton(self.sidebar_frame, text="4. Expert Insights", command=lambda: self.show_frame("insights"))
        self.btn_in.grid(row=4, column=0, padx=20, pady=10)

        # Main Container for Persistent Frames
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        # Initialize and stack frames
        self.frames = {
            "research": ResearchFrame(self.container, self),
            "linkedin": LinkedInFrame(self.container, self),
            "youtube": YouTubeFrame(self.container, self),
            "insights": InsightsFrame(self.container, self)
        }

        for frame in self.frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

        # Global Loading Overlay
        self.progress_bar = ctk.CTkProgressBar(self, orientation="horizontal", mode="indeterminate")
        self.loading_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12, slant="italic"))

        self.show_frame("research")

    def show_frame(self, name):
        """Raises the selected frame to the top and refreshes data if needed."""
        frame = self.frames[name]
        frame.tkraise()
        if hasattr(frame, "refresh_dropdown"):
            frame.refresh_dropdown()

    def start_loading(self, message):
        """Global loading indicator."""
        self.loading_label.configure(text=message)
        self.loading_label.place(relx=0.5, rely=0.04, anchor="center")
        self.progress_bar.place(relx=0.5, rely=0.07, anchor="center")
        self.progress_bar.start()

    def stop_loading(self):
        """Stops and hides global loading indicator."""
        self.progress_bar.stop()
        self.progress_bar.place_forget()
        self.loading_label.place_forget()

if __name__ == "__main__":
    app = ResearchStudio()
    app.mainloop()
