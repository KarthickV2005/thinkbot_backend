import requests
import json
import random
import time
import re

class ScraperAgent:
    def __init__(self, api_key: str, file_path: str):
        self.api_key = api_key
        self.file_path = file_path
        self.text_data = self._load_text()

    def _load_text(self) -> str:
        """Load preprocessed text (from ProcessorAgent output file)."""
        with open(self.file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
            
    def _validate_response(self, content: str) -> bool:
        """Validate that the response meets quality standards."""
        if not content or content.isspace():
            return False
            
        try:
            data = json.loads(content.strip())
            if not isinstance(data, dict):
                return False
                
            similar_ideas = data.get("similar_ideas", [])
            if not isinstance(similar_ideas, list) or len(similar_ideas) == 0:
                return False
                
            # Check if ideas have required fields and content
            return any(
                isinstance(idea, dict) 
                and idea.get("idea_name") 
                and idea.get("idea_description")
                and len(str(idea["idea_name"]).strip()) > 0
                and len(str(idea["idea_description"]).strip()) > 0
                for idea in similar_ideas
            )
        except:
            return False

    def _get_category(self, description: str) -> str:
        """Determine the category based on the description."""
        description = description.lower()
        
        categories = {
            'E-commerce': ['shop', 'retail', 'store', 'marketplace', 'commerce', 'sell'],
            'FinTech': ['payment', 'finance', 'bank', 'invest', 'money', 'trading'],
            'EdTech': ['education', 'learn', 'teach', 'student', 'school', 'course'],
            'HealthTech': ['health', 'medical', 'wellness', 'fitness', 'doctor', 'patient'],
            'AI/ML': ['ai', 'machine learning', 'artificial intelligence', 'predict', 'automate'],
            'SaaS': ['software', 'platform', 'service', 'cloud', 'subscription'],
            'Enterprise': ['business', 'enterprise', 'corporate', 'company', 'organization'],
            'Consumer': ['user', 'consumer', 'personal', 'individual', 'customer'],
            'Mobile': ['app', 'mobile', 'phone', 'ios', 'android'],
            'IoT': ['iot', 'device', 'sensor', 'hardware', 'smart home']
        }
        
        # Find the category with the most keyword matches
        max_matches = 0
        best_category = 'General'
        
        for category, keywords in categories.items():
            matches = sum(1 for keyword in keywords if keyword in description)
            if matches > max_matches:
                max_matches = matches
                best_category = category
        
        return best_category

    def _validate_mistral_response(self, content: str) -> bool:
        """Validate that the Mistral response meets quality standards."""
        if not content or content.isspace():
            return False
            
        try:
            data = json.loads(content.strip())
            if not isinstance(data, dict):
                return False
                
            similar_ideas = data.get("similar_ideas", [])
            if not isinstance(similar_ideas, list) or len(similar_ideas) == 0:
                return False
                
            # Check if at least one idea has required fields
            return any(
                isinstance(idea, dict) 
                and "idea_name" in idea 
                and "idea_description" in idea
                and len(idea["idea_name"].strip()) > 0
                and len(idea["idea_description"].strip()) > 0
                for idea in similar_ideas
            )
        except:
            return False

    def query_mistral(self, max_retries: int = 3) -> str:
        """
        Send preprocessed product idea text to OpenRouter Mistral-7B
        and get YC competitor startups using COSTAR framework with similarity scores.
        """
        url = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/IyappaKumaranS", # Add referer for API tracking
        }

        
        prompt = f"""
        Use the COSTAR framework to analyze and suggest similar startup ideas.

        C (Context): 
        The user has a product idea and wants to explore similar startups from Y Combinator.
        The input idea has already been preprocessed for clarity.
        Input Idea: "{self.text_data}"

        O (Objective): 
        Identify 10 real competitors or highly similar ideas from Y Combinator’s startup directory.
        Each result must include:
        - idea_name: Name of the startup
        - idea_description: Simple, clear explanation of what they actually do (one or two lines max).

        S (Style): 
        Keep the results structured, concise, and easy to read. 
        Avoid long paragraphs. Stick to factual summaries.

        T (Tone): 
        Professional, informative, and startup-research oriented. 
        Avoid marketing fluff, use neutral descriptive tone.

        A (Audience): 
        Startup founders, students, and innovators who want to understand competitors 
        or validate their idea against real YC companies.

        R (Response): 
        Return output in strict JSON format with a list of objects.
        Each object must contain:
        - "idea_name"
        - "idea_description"

        Example JSON structure:
        {{
          "similar_ideas": [
            {{
              "idea_name": "Startup X",
              "idea_description": "Helps users track expenses automatically using AI."
            }},
            {{
              "idea_name": "Startup Y",
              "idea_description": "Provides a platform for farmers to sell produce directly to consumers."
            }}
          ]
        }}

        Now, based on the given user idea, return exactly 10 similar startup ideas in this JSON format.
        """

        data = {
            "model": "mistralai/mistral-7b-instruct",
            "messages": [
                {"role": "system", "content": "You are a startup competitor research agent."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7  # Add some variation but keep it realistic
        }

        last_error = None
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, data=json.dumps(data))
                
                if response.status_code == 200:
                    try:
                        response_content = response.json()["choices"][0]["message"]["content"]
                        
                        if not response_content or response_content.isspace():
                            raise ValueError("Empty response from Mistral API")
                        
                        # Try multiple JSON parsing approaches
                        try:
                            data = json.loads(response_content.strip())
                        except json.JSONDecodeError:
                            # Look for JSON in the response
                            json_match = re.search(r'\{[\s\S]*\}', response_content)
                            if json_match:
                                data = json.loads(json_match.group())
                            else:
                                raise ValueError("No valid JSON found in response")
                        
                        # Validate and ensure required structure
                        if not isinstance(data, dict):
                            data = {"similar_ideas": []}
                        
                        if "similar_ideas" not in data:
                            data["similar_ideas"] = []
                        
                        # Clean a nd validate each idea
                        valid_ideas = []
                        for idea in data["similar_ideas"]:
                            if not isinstance(idea, dict):
                                continue
                                
                            # Ensure required fields exist and are non-empty
                            if not idea.get("idea_name") or not idea.get("idea_description"):
                                continue
                                
                            valid_ideas.append(idea)
                        
                        # Update with only valid ideas
                        data["similar_ideas"] = valid_ideas
                        
                        # If we have at least one valid idea, process them
                        if len(valid_ideas) > 0:
                            for i, idea in enumerate(valid_ideas):
                                # Dynamic similarity based on position
                                base_similarity = max(85 - (i * 10), 25)
                                variation = random.uniform(-5, 5)
                                similarity = max(1, min(100, base_similarity + variation))
                                
                                # Enrich idea data
                                idea["similarity"] = round(similarity)
                                idea["category"] = idea.get("category", self._get_category(idea["idea_description"]))
                            
                            return json.dumps(data, ensure_ascii=False, indent=2)
                        else:
                            # If no valid ideas found, try again
                            raise ValueError("No valid ideas found in response")
                            
                    except Exception as e:
                        last_error = str(e)
                        if attempt < max_retries - 1:  # Don't sleep on last attempt
                            time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                        
                elif response.status_code == 429:  # Rate limit
                    last_error = "Rate limit exceeded"
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                    continue
                    
                else:
                    last_error = f"HTTP {response.status_code}: {response.text}"
                    break  # Don't retry on other HTTP errors
                    
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue
                
        # If all retries failed, return structured error response
        return json.dumps({
            "similar_ideas": [],
            "error": f"Failed to get valid response after {max_retries} attempts. Last error: {last_error}"
        }, ensure_ascii=False, indent=2)



if __name__ == "__main__":
    api_key = "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"  
    file_path = r"S:\ThinkBot-new\backend\text_files\ecommerce.txt"  

    agent = ScraperAgent(api_key, file_path)
    competitors = agent.query_mistral()

    print("\n=== Competitors (COSTAR JSON) ===\n")
    print(competitors)