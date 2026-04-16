import threading
import webbrowser
import requests
import customtkinter as ctk
from tkinter import messagebox
from bs4 import BeautifulSoup
from scripts.research_studio.utils import get_experts_from_sources, save_markdown, clean_text, translate_if_not_english

class InsightsFrame(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.experts_data = []
        self.filtered_experts = []
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="Expert Insights & External Resources", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w", padx=20, pady=(0, 10))
        
        # Source Selection
        ctrl_frame = ctk.CTkFrame(self)
        ctrl_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        self.expert_dropdown = ctk.CTkOptionMenu(ctrl_frame, values=["Loading..."], command=self.on_expert_selected)
        self.expert_dropdown.grid(row=0, column=0, padx=10, pady=10)
        
        self.resource_dropdown = ctk.CTkOptionMenu(ctrl_frame, values=["Select Resource"], state="disabled")
        self.resource_dropdown.grid(row=0, column=1, padx=10)

        self.scrape_btn = ctk.CTkButton(ctrl_frame, text="🚀 Scrape Resource", state="disabled", command=self.run_threaded_scrape)
        self.scrape_btn.grid(row=0, column=2, padx=10)

        # Body/Preview Area
        self.res_text = ctk.CTkTextbox(self, font=ctk.CTkFont(size=14))
        self.res_text.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)

        self.save_btn = ctk.CTkButton(self, text="💾 Save to Research/Other", state="disabled", fg_color="green", command=self.save_insight)
        self.save_btn.grid(row=3, column=0, pady=10)

    def refresh_dropdown(self):
        self.experts_data = get_experts_from_sources()
        # Filter: Only show people with "other_links" (websites, blogs, etc.)
        self.filtered_experts = [e for e in self.experts_data if e.get("other_links")]
        
        names = [e['name'] for e in self.filtered_experts]
        if names:
            self.expert_dropdown.configure(values=names)
            self.expert_dropdown.set(names[0])
            self.on_expert_selected(names[0])
        else:
            self.expert_dropdown.configure(values=["No Experts with Websites"])
            self.expert_dropdown.set("No Experts with Websites")

    def on_expert_selected(self, name):
        expert = next((e for e in self.filtered_experts if e['name'] == name), None)
        if expert:
            labels = [link['label'] for link in expert['other_links']]
            self.resource_dropdown.configure(values=labels, state="normal")
            self.resource_dropdown.set(labels[0])
            self.scrape_btn.configure(state="normal")
        else:
            self.resource_dropdown.configure(values=["N/A"], state="disabled")
            self.scrape_btn.configure(state="disabled")

    def run_threaded_scrape(self):
        expert_name = self.expert_dropdown.get()
        resource_label = self.resource_dropdown.get()
        expert = next((e for e in self.filtered_experts if e['name'] == expert_name), None)
        link_data = next((l for l in expert['other_links'] if l['label'] == resource_label), None)
        
        if not link_data: return
        
        self.scrape_btn.configure(state="disabled")
        self.app.start_loading(f"Scraping insights from {link_data['url']}...")
        threading.Thread(target=self.execute_scrape, args=(expert_name, resource_label, link_data['url']), daemon=True).start()

    def execute_scrape(self, author, label, url):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Remove scripts and styles
            for script in soup(["script", "style"]):
                script.decompose()
                
            text = soup.get_text(separator="\n", strip=True)
            
            # Translate if needed
            translated = translate_if_not_english(text)
            cleaned = clean_text(translated)
            
            self.current_data = {
                "author": author,
                "title": f"{label} Insight",
                "content": f"SOURCE URL: {url}\n\nCONTENT:\n\n{cleaned}"
            }
            
            self.app.after(0, self.display_results)
        except Exception as e:
            self.app.after(0, lambda: messagebox.showerror("Scrape Error", str(e)))
        finally:
            self.app.after(0, self.app.stop_loading)
            self.app.after(0, lambda: self.scrape_btn.configure(state="normal"))

    def display_results(self):
        self.res_text.delete("1.0", "end")
        self.res_text.insert("1.0", self.current_data['content'])
        self.save_btn.configure(state="normal")

    def save_insight(self):
        save_markdown(self.current_data['author'], self.current_data['title'], self.current_data['content'], "other")
        messagebox.showinfo("Success", f"Insight saved to research/other/{self.current_data['author']}")
