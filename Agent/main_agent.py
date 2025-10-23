import json
from .processor_agent import ProcessorAgent
from .scraper_agent import ScraperAgent
from .validator import ValidatorAgent
from .enhancer_agent import EnhancerAgent


class MainAgent:
    def __init__(self, api_key: str, file_path: str):
        self.api_key = api_key
        self.file_path = file_path

    def run_pipeline(self):
        print("\n=== STEP 1: Preprocessing Idea ===\n")
        processor = ProcessorAgent()
        processed_text = processor.process_file(self.file_path)

        print("\n=== STEP 2: Finding Competitors ===\n")
        scraper = ScraperAgent(self.api_key, self.file_path)
        competitors_json = scraper.query_mistral()
        print(competitors_json)

        # Try parsing JSON to make it pretty
        try:
            competitors = json.loads(competitors_json)
        except Exception:
            competitors = []
        if isinstance(competitors, dict) and "similar_ideas" in competitors:
            competitors = competitors["similar_ideas"]
        elif not isinstance(competitors, list):
            competitors = []

        print("\n=== STEP 3: Validating Idea ===\n")
        validator = ValidatorAgent(self.api_key, self.file_path)
        validation_result = validator.query_mistral()
        print(validation_result)

        # Define score mappings for validation scores
        score_mappings = {
            "uniqueness": {
                "category": "Uniqueness",
                "color": "from-purple-400 to-pink-500",
                "explanation": "How original the idea is compared to existing solutions"
            },
            "feasibility": {
                "category": "Feasibility",
                "color": "from-green-400 to-emerald-500",
                "explanation": "Practicality of building and executing the idea"
            },
            "market_trend": {
                "category": "Market Trend",
                "color": "from-blue-400 to-indigo-500",
                "explanation": "Alignment with current and emerging market trends"
            },
            "scalability": {
                "category": "Scalability",
                "color": "from-orange-400 to-red-500",
                "explanation": "Ability to expand and grow at larger scale"
            },
            "problem_relevance": {
                "category": "Problem Relevance",
                "color": "from-cyan-400 to-blue-500",
                "explanation": "Importance of the problem being solved"
            },
            "user_adoption_potential": {
                "category": "User Adoption",
                "color": "from-yellow-400 to-orange-500",
                "explanation": "Likelihood that users will adopt this solution"
            }
        }

        # Structure validation scores
        scores = []
        try:
            val_data = json.loads(validation_result)
            if isinstance(val_data, dict) and "validation_scores" in val_data:
                for key, score in val_data["validation_scores"].items():
                    if key in score_mappings:
                        mapping = score_mappings[key]
                        scores.append({
                            "category": mapping["category"],
                            "score": int(float(score) * 10),  # Convert 0-10 score to percentage
                            "explanation": mapping["explanation"],
                            "color": mapping["color"]
                        })
        except Exception:
            scores = []

        print("\n=== STEP 4: Enhancing Idea ===\n")
        enhancer = EnhancerAgent(self.api_key, self.file_path)
        suggestions_text = enhancer.enhance_idea()
        print(suggestions_text)

        # Structure suggestions with proper format
        suggestions = []
        try:
            # Split suggestions text into individual points if it's a string
            if isinstance(suggestions_text, str):
                # Remove numbered lists if present (1., 2., etc)
                suggestions_list = [s.strip().replace(f"{i+1}.", "").strip() 
                                 for i, s in enumerate(suggestions_text.split("\n")) 
                                 if s.strip()]
                
                # Convert each suggestion into proper format with category and priority
                for i, sug in enumerate(suggestions_list):
                    if sug:
                        # Determine priority based on position (first suggestions are higher priority)
                        priority = "high" if i < 2 else "medium" if i < 4 else "low"
                        
                        suggestions.append({
                            "category": "Enhancement",
                            "tip": sug,
                            "priority": priority
                        })
        except Exception:
            suggestions = []

        # Structure competitors with required frontend fields
        structured_competitors = []
        if isinstance(competitors, list):
            for comp in competitors:
                if isinstance(comp, dict):
                    structured_competitors.append({
                        "name": comp.get("idea_name", "Unnamed Competitor"),
                        "description": comp.get("idea_description", ""),
                        "website": comp.get("website", ""),
                        "category": comp.get("category", "General"),
                        "similarity": float(comp.get("similarity", 50))
                    })

        return {
            "scores": scores,
            "suggestions": suggestions,
            "competitors": structured_competitors,
            "error": None,
        }


if __name__ == "__main__":
    API_KEY = "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"
    FILE_PATH = r"S:\ThinkBot-new\backend\text_files\ecommerce.txt"

    main = MainAgent(API_KEY, FILE_PATH)
    results = main.run_pipeline()

    print("\n=== FINAL SUMMARY ===\n")
    print(json.dumps(results, indent=2))
