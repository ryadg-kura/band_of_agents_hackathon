import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from agents.models import AgentOutput, RiskLevel, Vote

load_dotenv()
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

GEMINI_MODEL = "gemini-2.0-flash"

OUTPUT_FORMAT_INSTRUCTION = """
Réponds UNIQUEMENT avec un objet JSON valide, sans markdown, sans backticks.
Format exact :
{
  "risk_level": "HIGH" | "WARN" | "CLEAR",
  "confidence": 0.0 à 1.0,
  "reasoning": "explication détaillée en 2-3 phrases",
  "vote": "ESCALATE_SAR" | "ESCALATE_HUMAN" | "CLEAR"
}
"""


class BaseAgent:
    def __init__(self, agent_name: str, model_name: str = GEMINI_MODEL):
        self.agent_name = agent_name
        self.model = genai.GenerativeModel(model_name)

    def _call_llm(self, prompt: str) -> dict:
        response = self.model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())

    def _build_output(self, raw: dict, round_num: int) -> AgentOutput:
        return AgentOutput(
            agent=self.agent_name,
            round=round_num,
            risk_level=RiskLevel(raw["risk_level"]),
            confidence=float(raw["confidence"]),
            reasoning=raw["reasoning"],
            vote=Vote(raw["vote"]),
        )
