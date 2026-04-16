import threading
import webbrowser
import requests
import customtkinter as ctk
from tkinter import messagebox
from ddgs import DDGS
from slugify import slugify
from scripts.research_studio.utils import get_experts_from_sources, save_markdown, clean_text, translate_if_not_english

class LinkedInFrame(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.current_results = []
        self.experts_data = [] 
        self.selected_vars = [] 
        self.current_preview_url = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="LinkedIn Expert AI-SEO Scraper", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w", padx=20, pady=(0, 10))
        
        # Controls
        ctrl_frame = ctk.CTkFrame(self)
        ctrl_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        self.expert_dropdown = ctk.CTkOptionMenu(ctrl_frame, values=["Manual Input"])
        self.expert_dropdown.grid(row=0, column=0, padx=10, pady=10)
        
        self.post_title = ctk.CTkEntry(ctrl_frame, placeholder_text="Specific AI-SEO Keyword (Optional)", width=300)
        self.post_title.grid(row=0, column=1, padx=10)

        self.search_btn = ctk.CTkButton(ctrl_frame, text="🔍 Search Expert Posts", command=self.run_threaded_search)
        self.search_btn.grid(row=0, column=2, padx=10)

        self.select_btn = ctk.CTkButton(ctrl_frame, text="📋 Select Posts", state="disabled", fg_color="gray30", command=self.show_selection_dialog)
        self.select_btn.grid(row=0, column=3, padx=10)

        # Body/Preview Area
        self.post_body = ctk.CTkTextbox(self, font=ctk.CTkFont(size=14))
        self.post_body.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        
        self.post_body.tag_config("link", foreground="#1f538d", underline=True)
        self.post_body.tag_bind("link", "<Button-1>", lambda e: webbrowser.open(self.current_preview_url))
        self.post_body.tag_bind("link", "<Enter>", lambda e: self.post_body.configure(cursor="hand2"))
        self.post_body.tag_bind("link", "<Leave>", lambda e: self.post_body.configure(cursor=""))

        # Action Buttons
        action_frame = ctk.CTkFrame(self)
        action_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        
        ctk.CTkButton(action_frame, text="💾 Save Selected Posts", fg_color="green", command=self.save_selected_posts).grid(row=0, column=0, padx=10)
        self.open_browser_btn = ctk.CTkButton(action_frame, text="🌍 Open in Browser", fg_color="gray30", state="disabled", command=lambda: webbrowser.open(self.current_preview_url) if self.current_preview_url else None)
        self.open_browser_btn.grid(row=0, column=1, padx=10)
        ctk.CTkButton(action_frame, text="🗑️ Clear", fg_color="gray30", command=self.clear_all).grid(row=0, column=2, padx=10)

    def clear_all(self):
        self.post_body.delete("1.0", "end")
        self.current_preview_url = None
        self.open_browser_btn.configure(state="disabled")

    def refresh_dropdown(self):
        self.experts_data = get_experts_from_sources()
        names = [e['name'] for e in self.experts_data]
        self.expert_dropdown.configure(values=["Manual Input"] + names)

    def run_threaded_search(self):
        selected_name = self.expert_dropdown.get()
        keyword = self.post_title.get().strip()
        core_topic = "AI-powered SEO content production"
        
        selected_expert = next((e for e in self.experts_data if e['name'] == selected_name), None)
        
        self.search_btn.configure(state="disabled")
        self.app.start_loading(f"Searching posts by {selected_name} on AI-SEO...")
        threading.Thread(target=self.execute_search, args=(selected_expert, keyword, core_topic), daemon=True).start()

    def execute_search(self, expert, keyword, core_topic):
        try:
            date_filter = "2024 OR 2025 OR 2026"
            # Flexible keyword construction to avoid zero-results
            search_query = f"{core_topic} {keyword}".strip()
            
            queries = []
            if expert and expert.get('linkedin'):
                slug = expert['linkedin'].rstrip('/').split('/')[-1]
                # High-intent targeted search
                queries.append(f"site:linkedin.com/posts/{slug} {search_query} {date_filter}")
                # Fallback: Expert name + topic
                queries.append(f"site:linkedin.com/posts/ \"{expert['name']}\" AI SEO content {date_filter}")
            elif expert:
                queries.append(f"site:linkedin.com/posts/ \"{expert['name']}\" AI SEO production")
            else:
                # Manual input
                queries.append(f"site:linkedin.com/posts/ {search_query} {date_filter}")

            all_results = []
            with DDGS() as ddgs:
                for q in queries:
                    try:
                        results = list(ddgs.text(q, max_results=10))
                        all_results.extend(results)
                        if len(all_results) >= 10: break
                    except: continue

            unique_results = []
            seen_urls = set()
            for r in all_results:
                if r['href'] not in seen_urls:
                    # Broaden relevance check to ensure consistency
                    content_blob = (r['title'] + " " + r['body']).lower()
                    if any(key in content_blob for key in ["ai", "seo", "content", "search", "production"]):
                        unique_results.append(r)
                        seen_urls.add(r['href'])
            
            self.current_results = unique_results[:8]
            
            if not self.current_results:
                # Final fallback for DuckDuckGo inconsistency: try very broad
                with DDGS() as ddgs:
                    if expert:
                        broad_q = f"site:linkedin.com/posts/ \"{expert['name']}\" AI SEO"
                        self.current_results = list(ddgs.text(broad_q, max_results=5))

            if not self.current_results:
                self.app.after(0, lambda: messagebox.showinfo("No Results", f"Could not find recent AI-SEO posts for {expert['name'] if expert else 'this query'}. Try a broader keyword."))
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
        self.post_body.delete("1.0", "end")
        self.current_preview_url = result['href']
        self.post_body.insert("1.0", "LINK: ")
        self.post_body.insert("end", f"{result['href']}\n\n", "link")
        self.post_body.insert("end", f"TITLE: {result['title']}\n\n")
        self.post_body.insert("end", f"CONTENT PREVIEW:\n{result['body']}")
        self.open_browser_btn.configure(state="normal", fg_color="#1f538d")

    def show_selection_dialog(self):
        if not self.current_results: return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Select AI-SEO Posts")
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

    def save_selected_posts(self):
        author = self.expert_dropdown.get()
        if author == "Manual Input": author = "Unknown Author"
        selected_items = [res for res, var in zip(self.current_results, self.selected_vars) if var.get()]
        if not selected_items:
            messagebox.showwarning("Selection Required", "No posts selected.")
            return
        self.app.start_loading(f"Scraping & Translating {len(selected_items)} expert posts...")
        threading.Thread(target=self.execute_full_scrape, args=(author, selected_items), daemon=True).start()

    def execute_full_scrape(self, author, items):
        count = 0
        try:
            for res in items:
                url = res['href']
                title = res['title'].split(" - ")[0].split(" | ")[0].strip()
                if title.startswith(author):
                    title = title[len(author):].lstrip(": - |").strip()
                if not title: title = f"AI-SEO Post {url.split('/')[-1][:10]}"

                full_content = ""
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        main_content = soup.find('article') or soup.find('main')
                        full_content = main_content.get_text(separator="\n", strip=True) if main_content else res['body']
                    else:
                        full_content = res['body']
                except:
                    full_content = res['body']

                translated_text = translate_if_not_english(full_content)
                cleaned_content = clean_text(translated_text)
                final_output = f"**Source URL:** {url}\n\n**Full Content:**\n\n{cleaned_content}"
                save_markdown(author, title, final_output, "linkedin-posts")
                count += 1
            self.app.after(0, lambda: messagebox.showinfo("Success", f"Saved {count} posts authored by {author} on AI-SEO topic."))
        except Exception as e:
            self.app.after(0, lambda: messagebox.showerror("Scrape Error", str(e)))
        finally:
            self.app.after(0, self.app.stop_loading)
