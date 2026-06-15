import os
import json
from groq import Groq
from dotenv import load_dotenv
from agents.models import AgentOutput, RiskLevel, Vote

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"

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
    def __init__(self, agent_name: str, model_name: str = GROQ_MODEL):
        self.agent_name = agent_name
        self.model_name = model_name
        self.client = Groq(api_key=os.environ["GROQ_API_KEY"])

    def _call_llm(self, prompt: str) -> dict:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content.strip()
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
