import threading
import webbrowser
import requests
import customtkinter as ctk
from tkinter import messagebox
from ddgs import DDGS
from scripts.research_studio.config import SUPADATA_API_KEY
from scripts.research_studio.utils import get_experts_from_sources, save_markdown, clean_text, format_transcript, translate_if_not_english

class YouTubeFrame(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.current_results = []
        self.experts_data = [] 
        self.selected_vars = [] 
        self.current_preview_url = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="YouTube Expert AI-SEO Transcriber", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w", padx=20, pady=(0, 10))
        
        # Controls
        ctrl_frame = ctk.CTkFrame(self)
        ctrl_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        self.expert_dropdown = ctk.CTkOptionMenu(ctrl_frame, values=["Manual Input"])
        self.expert_dropdown.grid(row=0, column=0, padx=10, pady=10)
        
        self.search_entry = ctk.CTkEntry(ctrl_frame, placeholder_text="Specific AI-SEO Keyword (Optional)", width=300)
        self.search_entry.grid(row=0, column=1, padx=10)

        self.search_btn = ctk.CTkButton(ctrl_frame, text="🔍 Search Channel Videos", command=self.run_threaded_search)
        self.search_btn.grid(row=0, column=2, padx=10)

        self.select_btn = ctk.CTkButton(ctrl_frame, text="📋 Select Videos", state="disabled", fg_color="gray30", command=self.show_selection_dialog)
        self.select_btn.grid(row=0, column=3, padx=10)

        # Body/Preview Area
        self.res_text = ctk.CTkTextbox(self, font=ctk.CTkFont(size=14))
        self.res_text.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        
        self.res_text.tag_config("link", foreground="#1f538d", underline=True)
        self.res_text.tag_bind("link", "<Button-1>", lambda e: webbrowser.open(self.current_preview_url))
        self.res_text.tag_bind("link", "<Enter>", lambda e: self.res_text.configure(cursor="hand2"))
        self.res_text.tag_bind("link", "<Leave>", lambda e: self.res_text.configure(cursor=""))

        # Action Buttons
        action_frame = ctk.CTkFrame(self)
        action_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        
        ctk.CTkButton(action_frame, text="💾 Transcribe & Save Selected", fg_color="green", command=self.save_selected_transcripts).grid(row=0, column=0, padx=10)
        self.open_browser_btn = ctk.CTkButton(action_frame, text="🌍 Open in Browser", fg_color="gray30", state="disabled", command=lambda: webbrowser.open(self.current_preview_url) if self.current_preview_url else None)
        self.open_browser_btn.grid(row=0, column=1, padx=10)
        ctk.CTkButton(action_frame, text="🗑️ Clear", fg_color="gray30", command=self.clear_all).grid(row=0, column=2, padx=10)

    def clear_all(self):
        self.res_text.delete("1.0", "end")
        self.current_preview_url = None
        self.open_browser_btn.configure(state="disabled")

    def refresh_dropdown(self):
        all_experts = get_experts_from_sources()
        self.experts_data = [e for e in all_experts if e.get('youtube')]
        names = [e['name'] for e in self.experts_data]
        self.expert_dropdown.configure(values=["Manual Input"] + names)

    def run_threaded_search(self):
        selected_name = self.expert_dropdown.get()
        keyword = self.search_entry.get().strip()
        core_topic = "AI-powered SEO content production"
        
        selected_expert = next((e for e in self.experts_data if e['name'] == selected_name), None)
        
        self.search_btn.configure(state="disabled")
        self.app.start_loading(f"Searching {selected_name}'s YouTube for AI-SEO...")
        threading.Thread(target=self.execute_search, args=(selected_expert, keyword, core_topic), daemon=True).start()

    def execute_search(self, expert, keyword, core_topic):
        try:
            date_filter = "2024 OR 2025 OR 2026"
            search_query = f"{core_topic} {keyword}".strip()
            
            queries = []
            if expert and expert.get('youtube'):
                # Prioritize search WITHIN the specific channel
                queries.append(f"site:youtube.com/watch \"{expert['name']}\" {search_query} {date_filter}")
                # Fallback to general expert + topic search
                queries.append(f"site:youtube.com/watch \"{expert['name']}\" AI SEO production {date_filter}")
            elif expert:
                queries.append(f"site:youtube.com/watch \"{expert['name']}\" {search_query}")
            else:
                queries.append(f"site:youtube.com/watch {search_query} {date_filter}")

            all_results = []
            with DDGS() as ddgs:
                for q in queries:
                    try:
                        results = list(ddgs.text(q, max_results=10))
                        yt_links = [r for r in results if "youtube.com/watch" in r['href'] or "youtu.be/" in r['href']]
                        all_results.extend(yt_links)
                        if len(all_results) >= 10: break
                    except: continue

            unique_results = []
            seen_urls = set()
            for r in all_results:
                if r['href'] not in seen_urls:
                    content_blob = (r['title'] + " " + r['body']).lower()
                    if any(word in content_blob for word in ["seo", "ai", "content", "production", "search"]):
                        unique_results.append(r)
                        seen_urls.add(r['href'])
            
            self.current_results = unique_results[:5] 
            
            # Robust fallback for zero results
            if not self.current_results and expert:
                with DDGS() as ddgs:
                    fallback_q = f"site:youtube.com/watch \"{expert['name']}\" AI SEO"
                    self.current_results = list(ddgs.text(fallback_q, max_results=5))

            if not self.current_results:
                self.app.after(0, lambda: messagebox.showinfo("No Results", f"No specific AI-SEO videos found from {expert['name'] if expert else 'this query'}. Try broadening keywords."))
                self.app.after(0, lambda: self.select_btn.configure(state="disabled", fg_color="gray30"))
            else:
                self.app.after(0, lambda: self.select_btn.configure(state="normal", fg_color="#1f538d"))
                self.app.after(0, lambda: self.display_result(self.current_results[0]))
                
        except Exception as e:
            self.app.after(0, lambda: messagebox.showerror("Search Error", str(e)))
        finally:
            self.app.after(0, self.app.stop_loading)
            self.app.after(0, lambda: self.search_btn.configure(state="normal"))

    def display_result(self, result):
        self.res_text.delete("1.0", "end")
        self.current_preview_url = result['href']
        self.res_text.insert("1.0", "VIDEO LINK: ")
        self.res_text.insert("end", f"{result['href']}\n\n", "link")
        self.res_text.insert("end", f"TITLE: {result['title']}\n\n")
        self.res_text.insert("end", f"PREVIEW:\n{result['body']}")
        self.open_browser_btn.configure(state="normal", fg_color="#1f538d")

    def show_selection_dialog(self):
        if not self.current_results: return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Select Expert AI-SEO Videos")
        dialog.geometry("800x600")
        dialog.attributes("-topmost", True)
        header = ctk.CTkFrame(dialog)
        header.pack(fill="x", padx=10, pady=5)
        self.selected_vars = [ctk.BooleanVar(value=True) for _ in self.current_results]
        ctk.CTkButton(header, text="Select All", width=100, command=lambda: [v.set(True) for v in self.selected_vars]).pack(side="left", padx=5)
        ctk.CTkButton(header, text="Deselect All", width=100, command=lambda: [v.set(False) for v in self.selected_vars]).pack(side="left", padx=5)
        ctk.CTkButton(header, text="Done", width=100, fg_color="green", command=dialog.destroy).pack(side="right", padx=5)
        scroll_frame = ctk.CTkScrollableFrame(dialog)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        dialog.grab_set()
        for i, (res, var) in enumerate(zip(self.current_results, self.selected_vars)):
            f = ctk.CTkFrame(scroll_frame)
            f.pack(fill="x", pady=2)
            cb = ctk.CTkCheckBox(f, text=f"{i+1}. {res['title'][:90]}...", variable=var)
            cb.pack(side="left", padx=10, pady=5, fill="x", expand=True)
            ctk.CTkButton(f, text="🌍", width=30, command=lambda r=res: webbrowser.open(r['href'])).pack(side="right", padx=5)
            ctk.CTkButton(f, text="👁", width=30, command=lambda r=res: self.display_result(r)).pack(side="right", padx=5)

    def save_selected_transcripts(self):
        author = self.expert_dropdown.get()
        if author == "Manual Input": author = "Unknown Author"
        selected_items = [res for res, var in zip(self.current_results, self.selected_vars) if var.get()]
        if not selected_items:
            messagebox.showwarning("Selection Required", "No videos selected.")
            return
        self.app.start_loading(f"Transcribing & Translating {len(selected_items)} expert videos...")
        threading.Thread(target=self.execute_bulk_transcription, args=(author, selected_items), daemon=True).start()

    def execute_bulk_transcription(self, author, items):
        count = 0
        try:
            for res in items:
                url = res['href']
                title = res['title'].split(" - ")[0].split(" | ")[0].strip()
                try:
                    headers = {"x-api-key": SUPADATA_API_KEY}
                    resp = requests.get("https://api.supadata.ai/v1/youtube/transcript", headers=headers, params={"url": url})
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_content = data.get("content") or data.get("transcript") or ""
                        if isinstance(raw_content, list): 
                            raw_content = " ".join([i.get("text", "") for i in raw_content])
                        translated_text = translate_if_not_english(raw_content)
                        cleaned_text = clean_text(translated_text)
                        beautiful_content = format_transcript(cleaned_text)
                        video_author = data.get("author") or data.get("channel", {}).get("title") or author
                        final_output = f"**Video URL:** {url}\n\n**Transcript:**\n\n{beautiful_content}"
                        save_markdown(video_author, title, final_output, "youtube-transcripts")
                        count += 1
                except: continue
            self.app.after(0, lambda: messagebox.showinfo("Success", f"Saved {count} transcripts from {author}'s channel."))
        except Exception as e:
            self.app.after(0, lambda: messagebox.showerror("Transcription Error", str(e)))
        finally:
            self.app.after(0, self.app.stop_loading)
