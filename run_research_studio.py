import sys
from pathlib import Path

# Add the project root to the python path
root_dir = Path(__file__).parent
sys.path.append(str(root_dir))

if __name__ == "__main__":
    try:
        from scripts.research_studio.main import ResearchStudio
        app = ResearchStudio()
        app.mainloop()
    except ImportError as e:
        print(f"Error: {e}")
        print("\nEnsure you are running this from the project root and have installed all dependencies.")
        print("Run: pip install -r requirements.txt")
