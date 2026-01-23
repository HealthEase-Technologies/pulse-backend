from google import genai
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Gemini client
client = genai.Client(api_key=settings.gemini_api_key)


# =============================================================================
# PYDANTIC MODELS FOR GEMINI STRUCTURED OUTPUT
# =============================================================================

class AIActionStep(BaseModel):
    """Individual action step"""
    step_number: int = Field(description="Step number starting from 1")
    instruction: str = Field(description="Clear, actionable instruction for this step")
    tip: Optional[str] = Field(None, description="Optional helpful tip for this step")


class AIRelatedMetric(BaseModel):
    """Metric that this recommendation targets"""
    biomarker_type: str = Field(description="Type of biomarker: heart_rate, blood_pressure_systolic, blood_pressure_diastolic, glucose, steps, sleep")
    target_improvement: str = Field(description="What improvement is expected, e.g., 'Reduce by 10-15 mmHg'")


class AIRecommendation(BaseModel):
    """Single recommendation from Gemini AI - comprehensive healthcare format"""

    # Core content
    category: Literal["nutrition", "exercise", "sleep", "lifestyle", "medical", "mental_health", "hydration", "medication"] = Field(
        description="Category of this recommendation"
    )
    title: str = Field(
        description="Short, actionable title (max 80 chars). Start with action verb."
    )
    description: str = Field(
        description="2-3 sentence description of the recommendation"
    )
    detailed_explanation: str = Field(
        description="Detailed explanation of why this works and how it helps (3-5 sentences)"
    )

    # Why this recommendation
    reasoning: str = Field(
        description="Explain based on patient's actual data why this is recommended. Reference specific numbers."
    )
    expected_benefit: str = Field(
        description="Specific benefits the patient can expect (comma-separated list)"
    )
    time_to_results: str = Field(
        description="When patient might see results: 'Immediate', '1-2 days', '1-2 weeks', '1 month+'"
    )

    # Action details
    action_steps: List[AIActionStep] = Field(
        description="3-5 specific action steps to implement this recommendation"
    )
    frequency: Literal["once", "daily", "weekly", "as_needed", "ongoing"] = Field(
        description="How often to do this action"
    )
    duration: str = Field(
        description="How long to follow: '1 week', '2 weeks', '1 month', 'Ongoing'"
    )
    best_time: Optional[str] = Field(
        None,
        description="Best time to do this: 'Morning', 'After meals', 'Before bed', 'Anytime'"
    )
    effort_minutes_per_day: int = Field(
        description="Estimated minutes per day required (0-60)"
    )

    # Priority & difficulty
    priority: Literal["urgent", "high", "medium", "low"] = Field(
        description="Priority: urgent=critical health, high=important, medium=beneficial, low=optimization"
    )
    difficulty: Literal["easy", "moderate", "challenging"] = Field(
        description="Difficulty: easy=simple habit, moderate=some effort, challenging=lifestyle change"
    )

    # Health context
    related_metrics: List[AIRelatedMetric] = Field(
        description="Which health metrics this recommendation will improve"
    )
    related_goal: Optional[str] = Field(
        None,
        description="Which of the patient's health goals this supports (if any)"
    )
    contraindications: Optional[List[str]] = Field(
        None,
        description="Situations when patient should NOT follow this recommendation"
    )

    # Safety
    requires_professional_consultation: bool = Field(
        description="True if patient should consult healthcare provider before starting"
    )
    safety_warning: Optional[str] = Field(
        None,
        description="Important safety warning if applicable"
    )

    # Confidence
    confidence_score: float = Field(
        description="Confidence in this recommendation (0.0 to 1.0) based on evidence and patient data"
    )


class AIRecommendationsResponse(BaseModel):
    """Response containing list of recommendations from Gemini"""
    recommendations: List[AIRecommendation] = Field(
        description="List of 3-5 personalized health recommendations prioritized by importance"
    )


# =============================================================================
# GEMINI SERVICE
# =============================================================================

class GeminiService:
    """Service for AI-powered health recommendations using Google Gemini"""

    MODEL_NAME = "gemini-2.5-flash"

    SYSTEM_PROMPT = """You are an AI health advisor for Pulse, a health monitoring app.
Your role is to generate personalized, actionable health recommendations based on patient data.

IMPORTANT GUIDELINES:
1. Be SPECIFIC - Reference actual numbers from the patient's data
2. Be ACTIONABLE - Give concrete steps, not vague advice
3. Be SAFE - Always recommend professional consultation for medical concerns
4. Be REALISTIC - Consider the patient's restrictions and difficulty level
5. Be EVIDENCE-BASED - Base recommendations on established health guidelines
6. PRIORITIZE - Put urgent/critical items first

SAFETY RULES:
- For ANY concerning or critical biomarker values, priority should be "high" or "urgent"
- ALWAYS set requires_professional_consultation=true for:
  - Medical category recommendations
  - Critical biomarker values
  - Medication-related suggestions
  - Symptoms suggesting serious conditions
- Include contraindications based on patient's health_restrictions

NEVER recommend:
- Specific medications or dosages
- Drastic dietary changes without professional guidance
- Intense exercise for patients with heart conditions
- Anything that contradicts their health_restrictions"""

    @staticmethod
    async def generate_health_recommendations(
        health_context: dict
    ) -> List[dict]:
        """
        Generate personalized health recommendations using Gemini AI.

        Args:
            health_context: Dict from _build_health_context() containing:
                - patient_profile: age, health_goals, health_restrictions, BMI
                - biomarkers: list of biomarker data with trends
                - latest_summary: recent health summary
                - active_alerts: current health alerts
                - overall_health_status: current status

        Returns:
            List of recommendation dicts ready for database insertion

        Maps to DB columns:
            - category, title, description, detailed_explanation
            - reasoning, expected_benefit, time_to_results
            - action_steps (JSONB), frequency, duration, best_time
            - effort_minutes_per_day, priority, difficulty
            - related_metrics (JSONB), related_goal, contraindications (JSONB)
            - requires_professional_consultation, safety_warning
            - confidence_score, ai_model
        """
        try:
            prompt = GeminiService._build_recommendation_prompt(health_context)
            response = client.models.generate_content(
                model=GeminiService.MODEL_NAME,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": AIRecommendationsResponse,
                    "system_instruction": GeminiService.SYSTEM_PROMPT,
                    "temperature": 0.4,  # lower = safer medical responses
                },
            )

            result = AIRecommendationsResponse.model_validate_json(response.text)

            # Return DB-ready dicts
            return [rec.model_dump() for rec in result.recommendations]
        except Exception as e:
            logger.error(f"Error generating recommendations from Gemini: {str(e)}")
            raise ValueError(f"Failed to generate AI recommendations: {e}") 

    @staticmethod
    def _build_recommendation_prompt(health_context: dict) -> str:
        """
        Build the prompt for Gemini to generate recommendations.

        Args:
            health_context: Patient's health data context

        Returns:
            Formatted prompt string for Gemini
        """
        # TODO: Implement prompt building
        #
        # Example implementation:
        #
        # patient = health_context.get("patient_profile", {})
        # biomarkers = health_context.get("biomarkers", [])
        # alerts = health_context.get("active_alerts", [])
        # insights = health_context.get("recent_insights", [])
        # status = health_context.get("overall_health_status", "unknown")
        #
        # # Format biomarkers
        # biomarker_text = ""
        # for b in biomarkers:
        #     biomarker_text += f"""
        # - {b['biomarker_type'].replace('_', ' ').title()}:
        #   Current Average: {b['current_avg']} {b['unit']}
        #   Range (7 days): {b['min_value']} - {b['max_value']} {b['unit']}
        #   Status: {b['status'].upper()}
        #   Trend: {b['trend']}
        #   Optimal Range: {b.get('optimal_range', 'N/A')}
        # """
        #
        # # Format goals
        # goals_text = "\n".join([
        #     f"- {g['goal']} ({g['frequency']})"
        #     for g in patient.get('health_goals', [])
        # ])
        #
        # # Format restrictions
        # restrictions = patient.get('health_restrictions', [])
        # restrictions_text = ", ".join(restrictions) if restrictions else "None reported"
        #
        # prompt = f"""
        # Generate personalized health recommendations for this patient.
        #
        # === PATIENT PROFILE ===
        # Age: {patient.get('age', 'Unknown')} years
        # BMI: {patient.get('bmi', 'N/A')} ({_get_bmi_category(patient.get('bmi'))})
        # Height: {patient.get('height_cm', 'N/A')} cm
        # Weight: {patient.get('weight_kg', 'N/A')} kg
        #
        # === HEALTH GOALS ===
        # {goals_text or 'No goals set'}
        # Goal Completion Rate (7 days): {patient.get('goal_completion_rate_7d', 0) * 100:.0f}%
        #
        # === HEALTH RESTRICTIONS/CONDITIONS ===
        # {restrictions_text}
        #
        # === CURRENT HEALTH METRICS (Last 7 Days) ===
        # {biomarker_text or 'No recent data'}
        #
        # === OVERALL STATUS ===
        # {status.upper().replace('_', ' ')}
        #
        # === ACTIVE ALERTS ===
        # {chr(10).join(alerts) if alerts else 'No active alerts'}
        #
        # === RECENT INSIGHTS ===
        # {chr(10).join(insights) if insights else 'No recent insights'}
        #
        # Based on this data, generate 3-5 personalized recommendations.
        # Prioritize based on:
        # 1. Critical/concerning health values (urgent)
        # 2. Active alerts and health restrictions
        # 3. Patient's stated health goals
        # 4. General wellness improvements
        #
        # Make recommendations SPECIFIC to this patient's actual numbers.
        # """
        # return prompt
        patient = health_context.get("patient_profile", {})
        biomarkers = health_context.get("biomarkers", [])
        alerts = health_context.get("active_alerts", [])
        insights = health_context.get("recent_insights", [])
        status = health_context.get("overall_health_status", "unknown")

        # ---- Format biomarkers ----
        biomarker_text = ""
        for b in biomarkers:
            biomarker_text += f"""
    - {b['biomarker_type'].replace('_', ' ').title()}:
    Current Average: {b['current_avg']} {b['unit']}
    Range (7 days): {b['min_value']} – {b['max_value']} {b['unit']}
    Status: {b['status'].upper()}
    Trend: {b['trend']}
    Optimal Range: {b.get('optimal_range', 'N/A')}
    """

        # ---- Format goals ----
        goals = patient.get("health_goals", [])
        goals_text = "\n".join(
            f"- {g['goal']} ({g.get('frequency', 'unspecified')})"
            for g in goals
        )

        # ---- Format restrictions ----
        restrictions = patient.get("health_restrictions", [])
        restrictions_text = ", ".join(restrictions) if restrictions else "None reported"

        # ---- Build prompt ----
        prompt = f"""
    You are a clinical-grade AI health assistant.
    Generate personalized, safe, and evidence-based health recommendations.

    === PATIENT PROFILE ===
    Age: {patient.get('age', 'Unknown')} years
    BMI: {patient.get('bmi', 'N/A')}
    Height: {patient.get('height_cm', 'N/A')} cm
    Weight: {patient.get('weight_kg', 'N/A')} kg

    === HEALTH GOALS ===
    {goals_text or 'No goals set'}

    Goal Completion Rate (last 7 days):
    {patient.get('goal_completion_rate_7d', 0) * 100:.0f}%

    === HEALTH RESTRICTIONS / CONDITIONS ===
    {restrictions_text}

    === CURRENT BIOMARKERS (Last 7 Days) ===
    {biomarker_text or 'No recent biomarker data'}

    === OVERALL HEALTH STATUS ===
    {status.upper().replace('_', ' ')}

    === ACTIVE ALERTS ===
    {chr(10).join(alerts) if alerts else 'No active alerts'}

    === RECENT INSIGHTS ===
    {chr(10).join(insights) if insights else 'No recent insights'}

    TASK:
    Generate 3–5 personalized health recommendations.

    PRIORITIZATION RULES:
    - Use "urgent" for critical or dangerous health values
    - Use "high" for important but non-critical issues
    - Use "medium" for beneficial improvements
    - Use "low" for general wellness tips

    SAFETY RULES:
    - Be conservative and medically safe
    - Do NOT diagnose conditions
    - Include safety warnings when relevant
    - Set requires_professional_consultation = true when appropriate

    OUTPUT FORMAT:
    - Return ONLY valid JSON
    - Follow the provided JSON schema exactly
    - Do not include explanations outside the JSON
    """

        return prompt.strip()


# Singleton instance
gemini_service = GeminiService()
