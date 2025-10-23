import json
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from Agent.main_agent import MainAgent

app = FastAPI()

# Enable CORS for your frontend
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://thinkbot.web.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/run-pipeline")
async def run_pipeline(file: UploadFile = File(...), api_key: str = Form(...)):
    try:
        # Save the uploaded file temporarily
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Run the main agent pipeline
        main_agent = MainAgent(api_key, file_path)
        try:
            result = main_agent.run_pipeline()
            
            # Validate the result structure
            expected_fields = {"scores", "suggestions", "competitors"}
            if not all(field in result for field in expected_fields):
                missing = expected_fields - set(result.keys())
                for field in missing:
                    result[field] = []
            
            return result
        except json.JSONDecodeError as je:
            return {
                "scores": [],
                "suggestions": [],
                "competitors": [],
                "error": f"Invalid JSON response: {str(je)}",
            }
        except Exception as e:
            return {
                "scores": [],
                "suggestions": [],
                "competitors": [],
                "error": f"Pipeline error: {str(e)}",
            }

    except Exception as e:
        # Always return all expected fields for frontend compatibility
        return {
            "scores": [],
            "suggestions": [],
            "competitors": [],
            "error": f"File upload error: {str(e)}",
        }

@app.get("/")
def root():
    return {"message": "ThinkBot API is running 🚀"}
