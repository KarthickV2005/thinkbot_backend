import json
import requests
from .scraper_agent import ScraperAgent

class EnhancerAgent:
    def __init__(self, api_key: str, idea_file_path: str):
        self.api_key = api_key
        self.idea_file_path = idea_file_path
        self.model = "mistralai/mistral-7b-instruct"
        
    def _similarity_score(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using character-level comparison."""
        if not text1 or not text2:
            return 0.0
            
        # Convert to sets of words for comparison
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0

    def _load_idea(self) -> str:
        """Load user preprocessed idea text from file."""
        with open(self.idea_file_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    def enhance_idea(self) -> str:
        """Get competitors via ScraperAgent, then suggest improvements."""
        
        idea_text = self._load_idea()

    
        scraper = ScraperAgent(self.api_key, self.idea_file_path)
        competitors_json = scraper.query_mistral()

        try:
            competitors = json.loads(competitors_json)["similar_ideas"]
        except Exception:
            competitors = []

        
        comp_str = "\n".join(
            [f"- {c['idea_name']}: {c['idea_description']}" for c in competitors]
        )

        context = f"""
User Idea:
{idea_text}

Competitors from Y Combinator:
{comp_str}

Task:
Based on the above competitor context, provide actionable, clear,
and realistic suggestions to improve the uniqueness and value of
the user’s idea. Avoid hallucinations. Focus only on insights
that are not already covered by the listed competitors.
"""

       
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.model,
            "temperature": 0.7,
            "messages": [
                {"role": "system", "content": "You are a startup mentor. Give only factual, actionable suggestions."},
                {"role": "user", "content": context},
            ],
        }

        resp = requests.post(url, headers=headers, json=data)

        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"].strip()
            if not content:
                raise ValueError("Empty response from API")
            
            # Split into paragraphs/sections and clean up
            sections = content.split('\n\n')
            unique_sections = []
            seen_content = set()
            
            for section in sections:
                if not section.strip():
                    continue
                
                # Clean up the section
                lines = section.split('\n')
                cleaned_lines = []
                
                for line in lines:
                    # Basic cleanup
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Remove markdown and numbering
                    line = line.replace('*', '').replace('-', '')
                    if line and line[0].isdigit():
                        line = '.'.join(line.split('.')[1:]).strip()
                    line = line.lstrip('.-●•○◆◇■□▪️▫️►→').strip()
                    
                    if line:
                        cleaned_lines.append(line)
                
                if not cleaned_lines:
                    continue
                
                # Join lines in this section
                cleaned_section = ' '.join(cleaned_lines)
                
                # Check for near-duplicates using similarity score
                is_duplicate = False
                for seen in list(seen_content):
                    if (cleaned_section.lower() in seen.lower() or 
                        seen.lower() in cleaned_section.lower() or
                        self._similarity_score(cleaned_section, seen) > 0.7):
                        is_duplicate = True
                        break
                
                # Only add unique sections
                if not is_duplicate:
                    seen_content.add(cleaned_section)
                    unique_sections.append(cleaned_section)
            
            # Join unique sections with proper spacing
            cleaned_content = '\n\n'.join(unique_sections)
            return cleaned_content
        else:
            return f"Error: {resp.status_code}, {resp.text}"
        


if __name__ == "__main__":
    API_KEY = "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"  
    idea_file = r"S:\ThinkBot-new\backend\text_files\ecommerce.txt"

    enhancer = EnhancerAgent(API_KEY, idea_file)
    suggestions = enhancer.enhance_idea()

    print("\n--- Suggestions to Improve Idea ---\n")
    print(suggestions)