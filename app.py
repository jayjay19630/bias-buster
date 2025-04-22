import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import openai  # For AI-driven processing (case generation, categorization)
from fastapi import FastAPI
from pydantic import BaseModel
import json
import requests

# Load environment variables
load_dotenv()

# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# FastAPI for Backend Server
fastapi_app = FastAPI()

# Constants for responses
START_INVESTIGATION_TEXT = "*Starting a workplace fairness investigation for <@{user}>...*"
CASE_CREATED_TEXT = "*Case Created: The issue has been logged and is under review.*"
ISSUE_ESCALATED_TEXT = "*This issue has been escalated to HR/Management for further action.*"

# Step 2: Handle Slack Message (Request for Investigation)
@app.message("investigate|fairness|report")
def handle_investigation_request(message, say):
    user_id = message["user"]
    text = message["text"]

    # Respond that the investigation is starting
    say(text=START_INVESTIGATION_TEXT.format(user=user_id), thread_ts=message["ts"])

    # Process the request: Create the case automatically using AI
    case_data = process_case_request(text)

    # Step 3: Store the case and provide a case report to the user
    case_report = create_case_report(case_data)
    store_case_in_s3(case_report)  # Store case in AWS S3 (or another storage solution)

    # Send the case report back to the user
    say(text=CASE_CREATED_TEXT, thread_ts=message["ts"])

# Step 4: Process User Request to Create Case
def process_case_request(text):
    # Use AI model to categorize and process the case
    # You can use OpenAI GPT-3, or any NLP model to analyze the issue description
    case_category = "General Workplace Fairness"  # Example categorization
    case_details = text  # In real applications, you'd extract more details
    return {
        "category": case_category,
        "details": case_details,
        "status": "In Progress",
        "user": text.split(" ")[0],  # Just an example (first word as user)
    }

# Step 5: Create a Structured Case Report
def create_case_report(case_data):
    case_report = {
        "category": case_data["category"],
        "details": case_data["details"],
        "status": case_data["status"],
        "timestamp": str(os.time()),  # Use actual timestamp
        "user_id": case_data["user"],
    }
    return case_report

# Step 6: Store Case in AWS S3
def store_case_in_s3(case_report):
    s3_bucket_name = os.getenv("S3_BUCKET_NAME")
    s3_client = boto3.client('s3')
    case_report_json = json.dumps(case_report)
    
    # Upload to AWS S3
    s3_client.put_object(Bucket=s3_bucket_name, Key=f"case_reports/{case_report['timestamp']}.json", Body=case_report_json)

# Step 7: FastAPI Endpoint to Trigger Updates or View Cases
class CaseRequest(BaseModel):
    user_id: str
    issue_description: str

@fastapi_app.post("/submit_case")
async def submit_case(request: CaseRequest):
    case_data = process_case_request(request.issue_description)
    case_report = create_case_report(case_data)
    store_case_in_s3(case_report)
    return {"status": "Case Submitted", "case_report": case_report}

# Step 8: Start SlackBot Server
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()