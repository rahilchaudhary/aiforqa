from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
import json
import google.generativeai as genai
import re
import os

app = Flask(__name__)
load_dotenv()


# Configure Gemini
genai.configure(api_key=os.environ.get("GEN_AI_API_KEY"))
jenkins_user = os.environ.get("JENKINS_USER")
jenkins_token = os.environ.get("JENKINS_TOKEN")
jenkins_base_url = os.environ.get("JENKINS_URL")

# --- Agent ---
class JenkinsAIAgent:
    def __init__(self):
        genaiModel=os.environ.get("GENAI_MODEL","gemini-1.5-flash")
        self.model = genai.GenerativeModel(genaiModel)

    def parse_command(self, command_text):
        """Use Gemini to extract Jenkins parameters from plain English."""
        prompt = f"""
        You are a helper that extracts Jenkins command parameters from a plain English sentence.
        Extract these parameters:
        - product/application: the word after "for"
        - environment: the word after "on"
        - suite: words before "tests" or "cases"
        - type: type or layer of test (API, UI, Web)
        
        Respond ONLY in JSON:
        {{
          "product": "...",
          "environment": "...",
          "suite": "...",
          "type": "..."
        }}

        Sentence: "{command_text}"
        """
        response = self.model.generate_content(prompt)
        raw = re.sub(r"^```json|```$", "", response.text.strip())
        try:
            return json.loads(raw)
        except Exception as e:
            print("⚠️ JSON parse failed:", e)
            return {"product": None, "environment": None, "suite": None, "type": None}

    def trigger_jenkins(self, params):
        """Trigger Jenkins job with the extracted parameters."""
        auth = (jenkins_user, jenkins_token)
        try:
          # Extract parameters safely
            product = params.get("product")
            environment = params.get("environment")
            suite = params.get("suite")
            types = params.get("type")  # renamed to avoid conflict with built-in
            jobName = f"{product}_{types}_{suite}_{environment}"
            print ("Job Name -> ",jobName)
            jenkins_suffix=os.environ.get("JENKINS_SUFFIX","/buildWithParameters")
            job_url = f"{jenkins_base_url}{jobName}{jenkins_suffix}"
            if jenkins_suffix=="/build":
                response = requests.post(job_url,auth=auth)
            else:
                response = requests.post(job_url, params=params, auth=auth)
            print ("Job URL ->",job_url)
            if response.status_code in [200, 201]:
                return f"✅ Jenkins job triggered successfully: {jobName}"
            else:
                return f"⚠️ Jenkins failed ({response.status_code}): {response.text}"
        except Exception as e:
            return f"⚠️ Error triggering Jenkins: {e}"

    def handle_command(self, command_text):
        """Parse and trigger from plain English."""
        print(f"🔹 Received command: {command_text}")
        params = self.parse_command(command_text)
        print(f"🔹 Extracted params: {params}")
        result = self.trigger_jenkins(params)
        print(f"🔹 Result: {result}")
        return result

# Instantiate the agent
agent = JenkinsAIAgent()

# --- Flask endpoint ---
@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json

    if data.get("type") == "url_verification":
        return jsonify({"challenge": data["challenge"]})

    if "event" in data:
        event = data["event"]
        if event.get("type") == "app_mention":
            text = event.get("text", "")
            result = agent.handle_command(text)
            return jsonify({"text": result})

    return jsonify({"ok": True})

if __name__ == "__main__":
    flask_port=os.environ.get("FLASK_PORT",3000)
    app.run(port=flask_port)
