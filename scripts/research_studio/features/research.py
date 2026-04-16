import threading
import requests
import re
import customtkinter as ctk
from google import genai
from tkinter import messagebox
from ddgs import DDGS
from slugify import slugify
from scripts.research_studio.config import TAVILY_API_KEY, SOURCES_FILE, GEMINI_API_KEY
from scripts.research_studio.utils import clean_text

class ResearchFrame(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="B2B SaaS Market Research Agent", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w", padx=20, pady=(0, 10))
        
        # Search Controls
        ctrl_frame = ctk.CTkFrame(self)
        ctrl_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        self.search_entry = ctk.CTkEntry(ctrl_frame, placeholder_text="Enter Topic (e.g., AI SEO content production)", width=450)
        self.search_entry.grid(row=0, column=0, padx=10, pady=10)
        
        self.engine_dropdown = ctk.CTkOptionMenu(ctrl_frame, values=["Gemini (Expert AI)", "Tavily AI (Premium)", "DuckDuckGo (Free)"])
        self.engine_dropdown.grid(row=0, column=1, padx=10)
        
        self.search_btn = ctk.CTkButton(ctrl_frame, text="🚀 Run Research", command=self.run_threaded_search)
        self.search_btn.grid(row=0, column=2, padx=10)

        # Persistence Results Window
        self.res_text = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Segoe UI", size=14))
        self.res_text.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)

        # Control Buttons
        action_frame = ctk.CTkFrame(self)
        action_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        ctk.CTkButton(action_frame, text="Add Results to sources.md", fg_color="green", command=self.add_to_sources).grid(row=0, column=0, padx=10)
        ctk.CTkButton(action_frame, text="🗑️ Clear Results", fg_color="gray30", command=lambda: self.res_text.delete("1.0", "end")).grid(row=0, column=1, padx=10)

    def run_threaded_search(self):
        topic = self.search_entry.get().strip()
        if not topic: return
        self.search_btn.configure(state="disabled")
        self.app.start_loading(f"🕵️ Agent scanning for '{topic}'...")
        threading.Thread(target=self.execute_search, args=(topic,), daemon=True).start()

    def execute_search(self, topic):
        try:
            header_title = f"## Research source for {topic}"
            report = ""

            if "Gemini" in self.engine_dropdown.get():
                if not GEMINI_API_KEY: raise Exception("Missing GEMINI_API_KEY in .env")
                client = genai.Client(api_key=GEMINI_API_KEY)
                
                prompt = (f"As a Senior B2B SaaS Market Researcher, identify exactly 15 high-authority practitioner experts (founders, growth heads, or specialists) in '{topic}'. "
                         "For each expert, you MUST provide their Name, specific Expertise, and a unique 2024-2026 content pillar. "
                         "CRITICAL: You MUST also include their real LinkedIn profile URL and YouTube channel URL if they exist. "
                         "Output ONLY a Markdown table with these columns: | Expert Name | Expertise | Key Content Pillar | Research Folder & Links |. "
                         "In the last column, include: [LinkedIn](url), [YouTube](url), [Folder](./folder_name). "
                         "Format the folder name using slugify-style (lowercase, hyphens). "
                         "Do not include any preambles.")
                
                import time
                max_retries = 3
                retry_delay = 5
                
                for attempt in range(max_retries):
                    try:
                        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                        if response.text:
                            report = response.text.strip()
                        elif response.candidates and response.candidates[0].content.parts:
                            report = response.candidates[0].content.parts[0].text.strip()
                        else:
                            raise Exception("Empty response.")
                        break
                    except Exception as e:
                        if "429" in str(e) and attempt < max_retries - 1:
                            time.sleep(retry_delay * (attempt + 1))
                            continue
                        raise e
            
            elif "Tavily" in self.engine_dropdown.get():
                if not TAVILY_API_KEY: raise Exception("Missing TAVILY_API_KEY")
                persona_query = (f"Identify 15 practitioner experts in '{topic}'. Provide a Markdown table: "
                                 "| Expert Name | Expertise | Key Content Pillar | Research Folder & Links |. "
                                 "Include real LinkedIn and YouTube URLs in the last column.")
                
                resp = requests.post("https://api.tavily.com/search", json={
                    "api_key": TAVILY_API_KEY, 
                    "query": persona_query, 
                    "search_depth": "advanced",
                    "include_answer": True,
                    "max_results": 10
                })
                data = resp.json()
                report = data.get("answer", "")
                
                if not report or "|" not in report:
                    results = data.get("results", [])
                    table = "| Expert Name | Expertise | Key Content Pillar | Research Folder & Links |\n| :--- | :--- | :--- | :--- |\n"
                    for r in results:
                        name = r['title'].split("-")[0].split("|")[0].strip()
                        safe_name = slugify(name)
                        table += f"| **{name}** | {topic} | {r['content'][:100]}... | [Link]({r['url']}), [/research/youtube-transcripts/{safe_name}](./youtube-transcripts/{safe_name}) |\n"
                    report = table
            else:
                search_query = f"top 20 experts founders practitioners {topic} LinkedIn YouTube 2024"
                with DDGS() as ddgs:
                    results = list(ddgs.text(search_query, max_results=40))
                
                table = "| Expert Name | Expertise | Key Content Pillar | Research Folder & Links |\n| :--- | :--- | :--- | :--- |\n"
                seen_names = set()
                count = 0
                for r in results:
                    name = r['title'].split("-")[0].split("|")[0].split(":")[0].strip()
                    if len(name) < 4 or any(x in name.lower() for x in ["login", "search", "home", "about", "index"]):
                        continue
                    
                    if name.lower() not in seen_names:
                        safe_name = slugify(name)
                        pillar = r['body'].replace("|", " ").replace("\n", " ").strip()
                        # Detect if link is LinkedIn or YT
                        link_label = "Link"
                        if "linkedin.com" in r['href']: link_label = "LinkedIn"
                        elif "youtube.com" in r['href']: link_label = "YouTube"
                        
                        table += f"| **{name}** | {topic} | {pillar[:130]}... | [{link_label}]({r['href']}), [/research/youtube-transcripts/{safe_name}](./youtube-transcripts/{safe_name}) |\n"
                        seen_names.add(name.lower())
                        count += 1
                        if count >= 15: break
                report = table if count > 0 else "| No experts found | | | |"
            
            final_output = f"\n\n{header_title}\n\n{report}\n"
            self.app.after(0, lambda: self.res_text.insert("end", final_output))
        except Exception as e:
            self.app.after(0, lambda: messagebox.showerror("Search Error", str(e)))
        finally:
            self.app.after(0, self.app.stop_loading)
            self.app.after(0, lambda: self.search_btn.configure(state="normal"))

    def add_to_sources(self):
        content = self.res_text.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("Empty Results", "No research results to add.")
            return

        if messagebox.askyesno("Add to Sources", "Add all current results to sources.md?"):
            with open(SOURCES_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n\n{content}\n")
            messagebox.showinfo("Success", "Added research results to sources.md")
        else:
            self.open_manual_add_dialog()

    def open_manual_add_dialog(self):
        topic = self.search_entry.get().strip()
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Expert Manually")
        dialog.geometry("400x350")
        dialog.attributes("-topmost", True)

        ctk.CTkLabel(dialog, text="Expert Name:").pack(pady=(10, 0))
        name_entry = ctk.CTkEntry(dialog, width=300)
        name_entry.pack()

        ctk.CTkLabel(dialog, text="Expertise:").pack(pady=(10, 0))
        exp_entry = ctk.CTkEntry(dialog, width=300)
        exp_entry.pack()

        ctk.CTkLabel(dialog, text="Key Content Pillar:").pack(pady=(10, 0))
        pillar_entry = ctk.CTkEntry(dialog, width=300)
        pillar_entry.pack()

        def save():
            name = name_entry.get().strip()
            exp = exp_entry.get().strip()
            pillar = pillar_entry.get().strip()
            if not name: return

            safe_name = slugify(name)
            row = f"| **{name}** | {exp} | {pillar} | [/research/youtube-transcripts/{safe_name}](./youtube-transcripts/{safe_name}) |"
            
            header_title = f"## Research source for {topic}"
            file_content = ""
            if SOURCES_FILE.exists():
                with open(SOURCES_FILE, "r", encoding="utf-8") as f:
                    file_content = f.read()
            
            with open(SOURCES_FILE, "a", encoding="utf-8") as f:
                if header_title not in file_content:
                    f.write(f"\n\n{header_title}\n\n")
                    f.write("| Expert Name | Expertise | Key Content Pillar | Research Folder & Links |\n")
                    f.write("| :--- | :--- | :--- | :--- |\n")
                f.write(f"{row}\n")
            
            messagebox.showinfo("Success", f"Added {name} to sources.md")
            dialog.destroy()

        ctk.CTkButton(dialog, text="Add to Table", command=save, fg_color="green").pack(pady=20)
