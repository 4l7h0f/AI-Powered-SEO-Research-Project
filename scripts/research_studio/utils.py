import re
from slugify import slugify
from google import genai
from scripts.research_studio.config import SOURCES_FILE, BASE_PATH, GEMINI_API_KEY

def translate_if_not_english(text):
    """Translates text to English using Gemini if it's in another language."""
    if not text or not GEMINI_API_KEY: return text
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = (f"Identify the language of the following text. If it is NOT in English, translate it to clear, professional English. "
                 f"If it is already in English, return the exact original text. "
                 f"Do not include any preambles or explanations. "
                 f"Text: {text[:5000]}") # Limiting to 5000 chars for safety/speed
        
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        translated = response.text.strip()
        return translated if translated else text
    except:
        return text # Fallback to original on error

def clean_text(text):
    """Removes filler words and formats for readability without destroying URLs."""
    if not isinstance(text, str): text = str(text)
    
    # Improved URL protection regex
    url_pattern = r'https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+#]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, text)
    for i, url in enumerate(urls):
        text = text.replace(url, f"__URL_PLACEHOLDER_{i}__")

    fillers = [r'\buh-huh\b', r'\buh\b', r'\bum\b', r'\boh\b', r'\byou know\b', r'\blike\b', r'\bi mean\b']
    for filler in fillers:
        text = re.sub(filler, '', text, flags=re.IGNORECASE)
    
    # Format and capitalize
    text = re.sub(r'\s+', ' ', text).strip()
    if text:
        sentences = re.split(r'([.!?])\s+', text)
        text = ""
        for i in range(0, len(sentences)-1, 2):
            text += sentences[i].strip().capitalize() + sentences[i+1] + " "
        if len(sentences) % 2 != 0:
            text += sentences[-1].strip().capitalize()
    
    # Restore URLs
    for i, url in enumerate(urls):
        text = text.replace(f"__URL_PLACEHOLDER_{i}__", url)
        
    return text.strip()

def format_transcript(text):
    """Formats raw transcript into readable paragraphs."""
    # Break long text into paragraphs every ~4 sentences for a 'beautiful' view
    sentences = re.split(r'(?<=[.!?])\s+', text)
    paragraphs = []
    for i in range(0, len(sentences), 4):
        chunk = " ".join(sentences[i:i+4])
        paragraphs.append(chunk)
    return "\n\n".join(paragraphs)

def extract_expert_insights(text, source_url):
    """Extracts core insights, SEO implications, SOP rules, and citations using Gemini."""
    if not text or not GEMINI_API_KEY:
        return {
            "core_insight": "No content to analyze.",
            "seo_implication": "N/A",
            "sop_rule": "N/A",
            "citation": source_url
        }
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = (
            f"Analyze the following expert SEO content and extract these four specific sections:\n"
            f"1. Core insight: The main takeaway or discovery.\n"
            f"2. Implication for SEO: How this impacts SEO strategy or results.\n"
            f"3. Actionable rule (SOP line): A clear, step-by-step instruction for an Standard Operating Procedure.\n"
            f"4. Citation: A brief reference to the source (e.g., 'Author Name via LinkedIn').\n\n"
            f"Return the response in this EXACT format:\n"
            f"CORE INSIGHT: [insight]\n"
            f"SEO IMPLICATION: [implication]\n"
            f"SOP RULE: [rule]\n"
            f"CITATION: [citation]\n\n"
            f"Content: {text[:8000]}" # Limit context for speed/cost
        )
        
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        raw_text = response.text.strip()
        
        # Parse the response
        insights = {
            "core_insight": "N/A",
            "seo_implication": "N/A",
            "sop_rule": "N/A",
            "citation": source_url
        }
        
        patterns = {
            "core_insight": r"CORE INSIGHT:\s*(.*?)(?=SEO IMPLICATION:|SOP RULE:|CITATION:|$)",
            "seo_implication": r"SEO IMPLICATION:\s*(.*?)(?=CORE INSIGHT:|SOP RULE:|CITATION:|$)",
            "sop_rule": r"SOP RULE:\s*(.*?)(?=CORE INSIGHT:|SEO IMPLICATION:|CITATION:|$)",
            "citation": r"CITATION:\s*(.*?)(?=CORE INSIGHT:|SEO IMPLICATION:|SOP RULE:|$)"
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, raw_text, re.IGNORECASE | re.DOTALL)
            if match:
                insights[key] = match.group(1).strip()
                
        return insights
    except Exception as e:
        print(f"Insight extraction error: {e}")
        return {
            "core_insight": "Error processing content.",
            "seo_implication": "N/A",
            "sop_rule": "N/A",
            "citation": source_url
        }

def save_markdown(author, title, content, subfolder):
    """Saves content into structured markdown files."""
    safe_author = slugify(author)
    safe_title = slugify(title)
    
    dir_path = BASE_PATH / subfolder / safe_author
    dir_path.mkdir(parents=True, exist_ok=True)
    
    file_path = dir_path / f"{safe_title}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n")
        f.write(f"**Author:** {author}\n")
        f.write(f"**Source:** {subfolder}\n\n")
        f.write("## Content\n\n")
        f.write(content)
    return file_path

def get_experts_from_sources():
    """Parses sources.md for expert names and ALL key links from the entire row."""
    if not SOURCES_FILE.exists(): return []
    try:
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            experts = []
            for line in lines:
                if line.startswith("| **"):
                    # Extract name from the first bolded part
                    name_match = re.search(r'\*\*([^*]+)\*\*', line)
                    if not name_match: continue
                    name = name_match.group(1).strip()

                    # Find all LinkedIn and YouTube URLs anywhere in the line
                    li_match = re.search(r'(https?://www\.linkedin\.com/in/[^\s)|]+)', line)
                    yt_match = re.search(r'(https?://www\.youtube\.com/[^\s)|]+)', line)
                    
                    # Find other links (not LinkedIn or YouTube)
                    other_links = []
                    all_md_links = re.findall(r'\[([^\]]+)\]\((https?://[^)]+)\)', line)
                    for label, url in all_md_links:
                        if "linkedin" not in url.lower() and "youtube" not in url.lower():
                            other_links.append({"label": label, "url": url})
                    
                    experts.append({
                        "name": name, 
                        "linkedin": li_match.group(1).strip() if li_match else None,
                        "youtube": yt_match.group(1).strip() if yt_match else None,
                        "other_links": other_links
                    })
            return experts
    except: return []
