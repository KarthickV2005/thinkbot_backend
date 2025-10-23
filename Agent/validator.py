import requests
import json

class ValidatorAgent:
    def __init__(self, api_key: str, file_path: str):
        self.api_key = api_key
        self.file_path = file_path
        self.text_data = self._load_text()

    def _load_text(self) -> str:
        """Load preprocessed text (from ProcessorAgent output file)."""
        with open(self.file_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    def _analyze_competitors(self) -> tuple[float, list]:
        """Analyze competitors to get average similarity and top competitors."""
        from .scraper_agent import ScraperAgent
        
        # Get competitor analysis first
        scraper = ScraperAgent(self.api_key, self.file_path)
        competitors_json = scraper.query_mistral()
        
        try:
            data = json.loads(competitors_json)
            if "similar_ideas" in data:
                competitors = data["similar_ideas"]
                # Calculate average similarity
                similarities = [comp.get("similarity", 0) for comp in competitors]
                avg_similarity = sum(similarities) / len(similarities) if similarities else 0
                # Get top 3 most similar competitors
                top_competitors = sorted(competitors, key=lambda x: x.get("similarity", 0), reverse=True)[:3]
                return avg_similarity, top_competitors
        except:
            pass
        
        return 0, []

    def _validate_scores(self, data: dict) -> bool:
        """Validate that scores are present and within valid range."""
        if not isinstance(data, dict) or "validation_scores" not in data:
            return False
            
        scores = data["validation_scores"]
        if not isinstance(scores, dict):
            return False
            
        required_scores = [
            "uniqueness", "feasibility", "market_trend",
            "scalability", "problem_relevance", "user_adoption_potential"
        ]
        
        # Check if all required scores exist and are valid
        for score_name in required_scores:
            if score_name not in scores:
                return False
            try:
                score_value = float(scores[score_name])
                if not (0 <= score_value <= 10):
                    return False
            except (ValueError, TypeError):
                return False
                
        return True

    def query_mistral(self, max_retries: int = 3) -> str:
        """
        Validate the product idea using Mistral-7B and COSTAR framework.
        Returns structured JSON with validation scores.
        Includes retry logic for better reliability.
        """
        # First analyze competitors
        avg_similarity, top_competitors = self._analyze_competitors()
        
        # Convert competitor info to string for context
        competitor_context = "\n".join([
            f"- {comp['idea_name']}: {comp['idea_description']} (Similarity: {comp.get('similarity', 0)}%)"
            for comp in top_competitors
        ])

        url = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Detailed COSTAR prompt
        prompt = f"""
        As a startup validation expert, use the COSTAR framework to provide a detailed numerical assessment of this startup idea.
        You must provide specific numerical scores for each criterion. Scores MUST be between 0-10.

        C (Context): 
        Startup Idea: "{self.text_data}"
        
        Market Research:
        - Average Competitor Similarity: {avg_similarity}%
        - Competition Overview:
        {competitor_context}

        O (Objective): 
        Score each dimension from 0-10 using these specific criteria:

        1. Uniqueness Score (0-10):
        - Score 9-10: Highly unique, no direct competitors
        - Score 7-8: Novel approach in existing market
        - Score 5-6: Differentiated from competitors
        - Score 3-4: Similar to existing solutions
        - Score 1-2: Very similar to competitors
        Base this INVERSELY on competitor similarity: Higher similarity = LOWER score

        2. Feasibility Score (0-10):
        - Technical complexity (3 points)
        - Resource requirements (4 points)
        - Implementation timeline (3 points)
        Add points based on realistic implementation potential

        3. Market Trend Score (0-10):
        - Growing market (4 points)
        - Technology readiness (3 points)
        - User adoption readiness (3 points)
        Add points based on market timing and trends

        4. Scalability Score (0-10):
        - Market size potential (4 points)
        - Geographic expansion possible (3 points)
        - Revenue scaling potential (3 points)
        Add points based on growth potential

        5. Problem Relevance Score (0-10):
        - Pain point severity (4 points)
        - Target market size (3 points)
        - Problem urgency (3 points)
        Add points based on problem importance

        6. User Adoption Score (0-10):
        - Value proposition clarity (3 points)
        - Ease of adoption (4 points)
        - User benefit ratio (3 points)
        Add points based on likely user acceptance

        S (Style): 
        - Use structured analysis, be concise and clear.
        - Focus on providing scores rather than long paragraphs.
        - Keep each score strictly numeric (0–10).

        T (Tone): 
        Professional, objective, and evaluation-focused.
        Avoid exaggeration or marketing tone.

        A (Audience): 
        Startup founders, product managers, and investors looking to validate startup ideas.

        R (Response): 
        Return output in strict JSON format:
        {{
          "validation_scores": {{
            "uniqueness": <score_out_of_10>,
            "feasibility": <score_out_of_10>,
            "market_trend": <score_out_of_10>,
            "scalability": <score_out_of_10>,
            "problem_relevance": <score_out_of_10>,
            "user_adoption_potential": <score_out_of_10>
          }},
          "overall_score": <total_score_out_of_100>
        }}

        Rules:
        - Base uniqueness and market_trend scores INVERSELY on competitor similarity
        - Higher similarity = LOWER uniqueness score
        - Higher similarity = LOWER market opportunity score
        - Each attribute must have an integer score from 0 to 10
        - "overall_score" must be the sum of all attributes, out of 100
        - Do not include explanations, only return JSON
        - Ensure scores reflect the competitive landscape accurately
        """

        data = {
            "model": "mistralai/mistral-7b-instruct",
            "messages": [
                {"role": "system", "content": "You are a startup validation assistant."},
                {"role": "user", "content": prompt}
            ]
        }

        last_error = None
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, data=json.dumps(data))
                
                if response.status_code == 200:
                    try:
                        response_content = response.json()["choices"][0]["message"]["content"]
                        if not response_content or response_content.isspace():
                            raise ValueError("Empty response from API")
                            
                        # Try to parse JSON response
                        try:
                            parsed_data = json.loads(response_content.strip())
                        except json.JSONDecodeError:
                            # Try to extract JSON from text
                            import re
                            json_match = re.search(r'\{[\s\S]*\}', response_content)
                            if json_match:
                                parsed_data = json.loads(json_match.group())
                            else:
                                raise ValueError("No valid JSON found in response")
                        
                        # Validate scores
                        if self._validate_scores(parsed_data):
                            # If scores are valid, ensure proper number formatting
                            scores = parsed_data["validation_scores"]
                            for key in scores:
                                scores[key] = round(float(scores[key]))
                            
                            # Recalculate overall score
                            parsed_data["overall_score"] = sum(scores.values())
                            
                            return json.dumps(parsed_data, ensure_ascii=False, indent=2)
                        else:
                            raise ValueError("Invalid score values in response")
                            
                    except Exception as e:
                        last_error = str(e)
                        if attempt < max_retries - 1:  # Don't sleep on last attempt
                            import time
                            time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                        
                elif response.status_code == 429:  # Rate limit
                    last_error = "Rate limit exceeded"
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(2 ** attempt)
                    continue
                    
                else:
                    last_error = f"HTTP {response.status_code}: {response.text}"
                    break
                    
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    import time
                    time.sleep(1)
                continue
                
        # If all retries failed, return structured error response
        error_response = {
            "validation_scores": {
                "uniqueness": 0,
                "feasibility": 0,
                "market_trend": 0,
                "scalability": 0,
                "problem_relevance": 0,
                "user_adoption_potential": 0
            },
            "overall_score": 0,
            "error": f"Failed to get valid validation scores after {max_retries} attempts. Last error: {last_error}",
            "raw_response": response_content if 'response_content' in locals() else None
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    api_key = "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"  
    file_path = r"S:\ThinkBot-new\backend\text_files\ecommerce.txt"  

    agent = ValidatorAgent(api_key, file_path)
    validation_result = agent.query_mistral()

    print("\n=== Validation Result (COSTAR JSON) ===\n")
    print(validation_result)
