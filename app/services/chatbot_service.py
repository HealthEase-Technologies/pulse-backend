"""
AI Chatbot Service - COMPLETE Implementation with ALL Functions
Uses JSON Schema function declarations for Gemini compatibility
"""

import json
from typing import Dict, List, Any, Optional
from datetime import date, datetime, timedelta
from google import genai
from google.genai import types
from app.config.database import supabase_admin
from app.config.settings import settings
from app.services.patient_service import patient_service
from app.services.biomarker_service import biomarker_service
from app.services.recommendations_service import recommendations_service
from app.services.alert_service import alert_service
from app.services.threshold_service import threshold_service
from app.services.health_summary_service import health_summary_service
from app.services.note_service import note_service
from app.services.device_service import device_service
from app.services.connection_service import connection_service


class ChatbotService:
    """AI chatbot with COMPLETE health data access and actions"""

    def __init__(self):
        self.client = None
        self.model = "gemini-2.5-flash"

    def _ensure_initialized(self):
        if self.client is None:
            self.client = genai.Client(api_key=settings.gemini_api_key)

    def _get_system_instruction(self, user_name: str = "there") -> str:
        return f"""You are Pulse AI, {user_name}'s personal health assistant.

**Core Abilities:**
- View ALL health data (biomarkers, goals, recommendations, alerts, summaries, notes, devices, providers)
- Take ACTIONS (add/remove goals, connect devices, acknowledge alerts, add biomarkers, mark notes as read)
- Interactive guidance with beautiful formatting

**Tone:** Friendly, encouraging, actionable. Use {user_name}'s name naturally.

**FORMATTING RULES (CRITICAL):**

1. **Data Display - Make it BEAUTIFUL:**
   - Use ## Headers for sections
   - Use **bold** for all numbers, values, and key metrics
   - Use bullet lists (-) with emojis for items
   - Add visual separators with ---
   - Example:
     ```
     ## 📊 Your Health Goals

     **Daily Goals:**
     - 💧 Drink 8 glasses of water
     - 🏃 Walk 10,000 steps

     **Completion Rate:** **85%** this week
     ---
     ```

2. **Lists with Actions - Present OPTIONS:**
   - When showing devices, notes, alerts, recommendations - LIST them with numbers
   - Tell user they can choose by number or name
   - Example:
     ```
     ## 🔔 Unread Alerts

     1. **Heart Rate Alert** - Your heart rate was **145 bpm** at 2:30 PM (Warning)
     2. **Glucose Alert** - Glucose spike to **180 mg/dL** detected (Critical)

     Would you like me to mark any as read? Just say the number or "mark all as read"!
     ```

3. **Forms & Interactive Inputs:**
   - When adding goals, devices, biomarkers - ASK step by step
   - Example for adding goal:
     ```
     Great! Let's add a new health goal.

     **What's your goal?** (e.g., "Drink 8 glasses of water", "Exercise for 30 minutes")
     ```
   - Then ask frequency:
     ```
     Perfect! **How often?**
     - Daily
     - Weekly
     - Monthly
     ```

4. **Confirmations:**
   - Before taking actions, CONFIRM with clear summary
   - Example:
     ```
     ## ✅ Confirm Action

     **Goal to add:**
     - Goal: Drink 8 glasses of water
     - Frequency: Daily

     Should I add this goal? (Yes/No)
     ```

5. **Device Connection:**
   - First call get_available_device_types()
   - Show beautiful list with emojis
   - Guide through connection
   - Example:
     ```
     ## 📱 Available Devices

     1. ⌚ **Apple Watch** - Track heart rate, steps, sleep
     2. 📊 **Glucose Monitor** - Continuous glucose monitoring
     3. 💪 **Fitbit** - Activity and fitness tracking

     Which device would you like to connect? (Say number or name)
     ```

6. **Provider Notes:**
   - Display with timestamp, provider name
   - Show "Mark as Read" option
   - Example:
     ```
     ## 📝 Recent Notes from Your Provider

     **1. Dr. Smith** (Feb 15, 2026)
     > Your blood pressure readings look good. Continue current medication.

     **2. Dr. Smith** (Feb 10, 2026)
     > Follow up on glucose levels next week.

     Say "mark note 1 as read" or "mark all as read"
     ```

7. **Thresholds:**
   - When showing thresholds, format clearly with ranges
   - Explain what each means
   - Example:
     ```
     ## ⚙️ Your Health Thresholds

     **Heart Rate:**
     - Normal: **60-100 bpm**
     - Warning: **100-120 bpm**
     - Critical: **>120 bpm**

     **Glucose:**
     - Normal: **70-140 mg/dL**
     - Warning: **140-180 mg/dL**
     - Critical: **>180 mg/dL**

     These are customized for you. Would you like to adjust any?
     ```

**ALWAYS:**
- Call functions to get REAL data
- Format responses beautifully with emojis, headers, bold
- Present clear action options
- Guide users step-by-step
- Confirm before taking actions"""

    def _get_function_declarations(self) -> List[Dict[str, Any]]:
        """JSON Schema function declarations for Gemini"""

        return [
            # ===== PROFILE & GOALS =====
            {
                "name": "get_patient_profile",
                "description": "Get complete patient profile including personal info, health goals, and restrictions",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "update_patient_profile",
                "description": "Update patient profile information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "height_cm": {
                            "type": "number",
                            "description": "Height in centimeters"
                        },
                        "weight_kg": {
                            "type": "number",
                            "description": "Weight in kilograms"
                        },
                        "health_restrictions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of health restrictions or conditions"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_goal_stats",
                "description": "Get goal statistics including total goals, completed count, completion rate, and streaks",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_goal_completions",
                "description": "Get goal completion history within a date range",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "mark_goal_complete",
                "description": "Mark a health goal as completed for a specific date",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "goal_text": {
                            "type": "string",
                            "description": "Exact goal text from the patient's profile"
                        },
                        "goal_frequency": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly"],
                            "description": "Goal frequency"
                        },
                        "completion_date": {
                            "type": "string",
                            "description": "Completion date in YYYY-MM-DD format (defaults to today if not provided)"
                        }
                    },
                    "required": ["goal_text", "goal_frequency"]
                }
            },
            {
                "name": "unmark_goal_complete",
                "description": "Remove a goal completion for a specific date",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "goal_text": {
                            "type": "string",
                            "description": "Exact goal text"
                        },
                        "completion_date": {
                            "type": "string",
                            "description": "Completion date in YYYY-MM-DD format"
                        }
                    },
                    "required": ["goal_text", "completion_date"]
                }
            },
            {
                "name": "add_new_goal",
                "description": "Add a new health goal to the patient's profile",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "goal_text": {
                            "type": "string",
                            "description": "The goal description/text"
                        },
                        "goal_frequency": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly"],
                            "description": "How often the goal should be completed"
                        }
                    },
                    "required": ["goal_text", "goal_frequency"]
                }
            },
            {
                "name": "remove_goal",
                "description": "Remove a health goal from the patient's profile",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "goal_text": {
                            "type": "string",
                            "description": "Exact goal text to remove"
                        }
                    },
                    "required": ["goal_text"]
                }
            },

            # ===== BIOMARKERS =====
            {
                "name": "get_biomarker_dashboard",
                "description": "Get latest biomarker readings for all biomarker types",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_biomarker_history",
                "description": "Get historical biomarker data for a specific type",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "biomarker_type": {
                            "type": "string",
                            "enum": ["heart_rate", "blood_pressure_systolic", "blood_pressure_diastolic", "glucose", "steps", "sleep"],
                            "description": "Type of biomarker"
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of days to look back (default 7)",
                            "default": 7
                        }
                    },
                    "required": ["biomarker_type"]
                }
            },
            {
                "name": "add_biomarker_reading",
                "description": "Add a new biomarker reading",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "biomarker_type": {
                            "type": "string",
                            "enum": ["heart_rate", "blood_pressure_systolic", "blood_pressure_diastolic", "glucose", "steps", "sleep"],
                            "description": "Type of biomarker"
                        },
                        "value": {
                            "type": "number",
                            "description": "The measurement value"
                        },
                        "recorded_at": {
                            "type": "string",
                            "description": "ISO timestamp (optional, defaults to now)"
                        }
                    },
                    "required": ["biomarker_type", "value"]
                }
            },

            # ===== RECOMMENDATIONS =====
            {
                "name": "get_active_recommendations",
                "description": "Get active AI health recommendations, optionally filtered by category",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["nutrition", "exercise", "sleep", "lifestyle", "medical", "mental_health", "hydration", "medication"],
                            "description": "Filter by recommendation category"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "start_recommendation",
                "description": "Mark a recommendation as started/in progress",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "recommendation_id": {
                            "type": "string",
                            "description": "ID of the recommendation to start"
                        }
                    },
                    "required": ["recommendation_id"]
                }
            },
            {
                "name": "complete_recommendation",
                "description": "Mark a recommendation as completed",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "recommendation_id": {
                            "type": "string",
                            "description": "ID of the recommendation to complete"
                        }
                    },
                    "required": ["recommendation_id"]
                }
            },
            {
                "name": "dismiss_recommendation",
                "description": "Dismiss a recommendation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "recommendation_id": {
                            "type": "string",
                            "description": "ID of the recommendation to dismiss"
                        }
                    },
                    "required": ["recommendation_id"]
                }
            },

            # ===== ALERTS =====
            {
                "name": "get_alert_history",
                "description": "Get alert history, optionally filtered by type",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of alerts to return (default 50)",
                            "default": 50
                        },
                        "alert_type": {
                            "type": "string",
                            "enum": ["warning", "critical"],
                            "description": "Filter by alert severity"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_unacknowledged_alerts",
                "description": "Get count of unacknowledged/unread alerts",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "acknowledge_alert",
                "description": "Mark an alert as acknowledged/read",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "alert_id": {
                            "type": "string",
                            "description": "ID of the alert to acknowledge"
                        }
                    },
                    "required": ["alert_id"]
                }
            },
            {
                "name": "get_effective_thresholds",
                "description": "Get health thresholds (patient-specific if set, otherwise system defaults)",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "update_patient_threshold",
                "description": "Update or create a custom health threshold for the patient",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "biomarker_type": {
                            "type": "string",
                            "enum": ["heart_rate", "blood_pressure_systolic", "blood_pressure_diastolic", "glucose", "steps", "sleep"],
                            "description": "Type of biomarker"
                        },
                        "min_normal": {
                            "type": "number",
                            "description": "Minimum normal value"
                        },
                        "max_normal": {
                            "type": "number",
                            "description": "Maximum normal value"
                        },
                        "min_warning": {
                            "type": "number",
                            "description": "Minimum warning value (optional)"
                        },
                        "max_warning": {
                            "type": "number",
                            "description": "Maximum warning value (optional)"
                        },
                        "min_critical": {
                            "type": "number",
                            "description": "Minimum critical value (optional)"
                        },
                        "max_critical": {
                            "type": "number",
                            "description": "Maximum critical value (optional)"
                        }
                    },
                    "required": ["biomarker_type", "min_normal", "max_normal"]
                }
            },

            # ===== SUMMARIES =====
            {
                "name": "get_todays_summary",
                "description": "Get today's health summary (morning briefing or evening summary)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary_type": {
                            "type": "string",
                            "enum": ["morning_briefing", "evening_summary"],
                            "description": "Type of summary to retrieve"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_summaries_range",
                "description": "Get health summaries for a date range",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format"
                        }
                    },
                    "required": ["start_date", "end_date"]
                }
            },

            # ===== NOTES =====
            {
                "name": "get_my_notes",
                "description": "Get notes from healthcare provider",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of notes to return (default 50)",
                            "default": 50
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "mark_note_as_read",
                "description": "Mark a provider note as read",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "ID of the note to mark as read"
                        }
                    },
                    "required": ["note_id"]
                }
            },

            # ===== DEVICES =====
            {
                "name": "get_connected_devices",
                "description": "Get user's connected health devices",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["connected", "disconnected"],
                            "description": "Filter by device connection status"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_available_device_types",
                "description": "Get list of available device types that can be connected",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "connect_device",
                "description": "Connect a new health device",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "device_type": {
                            "type": "string",
                            "description": "Type of device to connect (from available device types)"
                        },
                        "device_name": {
                            "type": "string",
                            "description": "Custom name for the device (optional)"
                        }
                    },
                    "required": ["device_type"]
                }
            },
            {
                "name": "disconnect_device",
                "description": "Disconnect a health device",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "device_id": {
                            "type": "string",
                            "description": "ID of the device to disconnect"
                        }
                    },
                    "required": ["device_id"]
                }
            },

            # ===== PROVIDER CONNECTIONS =====
            {
                "name": "get_my_providers",
                "description": "Get connected healthcare providers",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "request_provider_connection",
                "description": "Send connection request to a healthcare provider",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "provider_user_id": {
                            "type": "string",
                            "description": "User ID of the provider to connect with"
                        }
                    },
                    "required": ["provider_user_id"]
                }
            },
            {
                "name": "disconnect_from_provider",
                "description": "Disconnect from a healthcare provider",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "connection_id": {
                            "type": "string",
                            "description": "ID of the connection to remove"
                        }
                    },
                    "required": ["connection_id"]
                }
            },
        ]

    async def _execute_function(self, user_id: str, function_name: str, args: Dict[str, Any]) -> Any:
        """Execute a function call and return the result"""

        # ===== PROFILE & GOALS =====
        if function_name == "get_patient_profile":
            return await patient_service.get_patient_profile(user_id)

        elif function_name == "update_patient_profile":
            update_data = {}
            if "height_cm" in args:
                update_data["height_cm"] = args["height_cm"]
            if "weight_kg" in args:
                update_data["weight_kg"] = args["weight_kg"]
            if "health_restrictions" in args:
                update_data["health_restrictions"] = args["health_restrictions"]
            return await patient_service.update_patient_profile(user_id, update_data)

        elif function_name == "get_goal_stats":
            return await patient_service.get_goal_stats(user_id)

        elif function_name == "get_goal_completions":
            return await patient_service.get_goal_completions(
                user_id,
                args.get("start_date"),
                args.get("end_date")
            )

        elif function_name == "mark_goal_complete":
            completion_date = args.get("completion_date", date.today().isoformat())
            return await patient_service.mark_goal_complete(
                user_id,
                args["goal_text"],
                args["goal_frequency"],
                completion_date
            )

        elif function_name == "unmark_goal_complete":
            return await patient_service.unmark_goal_complete(
                user_id,
                args["goal_text"],
                args["completion_date"]
            )

        elif function_name == "add_new_goal":
            # Get current profile
            profile = await patient_service.get_patient_profile(user_id)
            if not profile:
                return {"error": "Profile not found"}

            # Get existing goals or initialize empty array
            current_goals = profile.get("health_goals", [])

            # Check if goal already exists
            goal_exists = any(
                g.get("goal") == args["goal_text"] and g.get("frequency") == args["goal_frequency"]
                for g in current_goals
            )

            if goal_exists:
                return {"error": "This goal already exists", "success": False}

            # Add new goal
            new_goal = {
                "goal": args["goal_text"],
                "frequency": args["goal_frequency"]
            }
            current_goals.append(new_goal)

            # Update profile
            result = await patient_service.update_patient_profile(user_id, {
                "health_goals": current_goals
            })

            return {"success": True, "message": "Goal added successfully", "goal": new_goal}

        elif function_name == "remove_goal":
            # Get current profile
            profile = await patient_service.get_patient_profile(user_id)
            if not profile:
                return {"error": "Profile not found"}

            # Get existing goals
            current_goals = profile.get("health_goals", [])

            # Remove the goal
            updated_goals = [
                g for g in current_goals
                if g.get("goal") != args["goal_text"]
            ]

            if len(updated_goals) == len(current_goals):
                return {"error": "Goal not found", "success": False}

            # Update profile
            result = await patient_service.update_patient_profile(user_id, {
                "health_goals": updated_goals
            })

            return {"success": True, "message": "Goal removed successfully"}

        # ===== BIOMARKERS =====
        elif function_name == "get_biomarker_dashboard":
            return await biomarker_service.get_latest_biomarker_readings(user_id)

        elif function_name == "get_biomarker_history":
            days = args.get("days", 7)
            history = await biomarker_service.get_biomarker_history(user_id, args["biomarker_type"], 200, 0)
            from datetime import timezone
            from dateutil import parser
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            filtered = []
            for r in history:
                try:
                    recorded_at = parser.parse(r["recorded_at"])
                    if recorded_at >= cutoff:
                        filtered.append(r)
                except Exception:
                    continue
            return filtered

        elif function_name == "add_biomarker_reading":
            recorded_at = args.get("recorded_at", datetime.now().isoformat())
            return await biomarker_service.insert_biomarker_data(
                user_id,
                args["biomarker_type"],
                args["value"],
                recorded_at
            )

        # ===== RECOMMENDATIONS =====
        elif function_name == "get_active_recommendations":
            return await recommendations_service.get_active_recommendations(
                user_id,
                args.get("category")
            )

        elif function_name == "start_recommendation":
            return await recommendations_service.start_recommendation(args["recommendation_id"], user_id)

        elif function_name == "complete_recommendation":
            return await recommendations_service.complete_recommendation(args["recommendation_id"], user_id)

        elif function_name == "dismiss_recommendation":
            return await recommendations_service.dismiss_recommendation(args["recommendation_id"], user_id)

        # ===== ALERTS =====
        elif function_name == "get_alert_history":
            result = await alert_service.get_alert_history(
                user_id,
                args.get("limit", 50),
                0,
                args.get("alert_type")
            )
            return result.get("alerts", [])

        elif function_name == "get_unacknowledged_alerts":
            return await alert_service.get_unacknowledged_count(user_id)

        elif function_name == "acknowledge_alert":
            return await alert_service.acknowledge_alert(args["alert_id"], user_id)

        elif function_name == "get_effective_thresholds":
            return await threshold_service.get_effective_thresholds(user_id)

        elif function_name == "update_patient_threshold":
            return await threshold_service.upsert_patient_threshold(
                patient_user_id=user_id,
                biomarker_type=args["biomarker_type"],
                min_normal=args["min_normal"],
                max_normal=args["max_normal"],
                min_warning=args.get("min_warning"),
                max_warning=args.get("max_warning"),
                min_critical=args.get("min_critical"),
                max_critical=args.get("max_critical")
            )

        # ===== SUMMARIES =====
        elif function_name == "get_todays_summary":
            return await health_summary_service.get_user_summary(
                user_id,
                date.today(),
                args.get("summary_type")
            )

        elif function_name == "get_summaries_range":
            return await health_summary_service.get_user_summaries_range(
                user_id,
                args["start_date"],
                args["end_date"]
            )

        # ===== NOTES =====
        elif function_name == "get_my_notes":
            return await note_service.get_my_notes(user_id, args.get("limit", 50), 0)

        elif function_name == "mark_note_as_read":
            return await note_service.mark_note_as_read(args["note_id"], user_id)

        # ===== DEVICES =====
        elif function_name == "get_connected_devices":
            return await device_service.get_user_devices(user_id, args.get("status"))

        elif function_name == "get_available_device_types":
            return await device_service.get_available_device_types()

        elif function_name == "connect_device":
            return await device_service.connect_device(
                user_id,
                args["device_type"],
                args.get("device_name")
            )

        elif function_name == "disconnect_device":
            return await device_service.disconnect_device(args["device_id"], user_id)

        # ===== PROVIDER CONNECTIONS =====
        elif function_name == "get_my_providers":
            result = await connection_service.get_patient_connections(user_id, status="accepted")
            return result.get("connections", [])

        elif function_name == "request_provider_connection":
            return await connection_service.request_connection(user_id, args["provider_user_id"])

        elif function_name == "disconnect_from_provider":
            return await connection_service.disconnect_from_provider(args["connection_id"], user_id)

        else:
            raise ValueError(f"Unknown function: {function_name}")

    async def chat(self, user_id: str, message: str, chat_history: List[Dict[str, str]] = None) -> str:
        """Chat with manual function calling"""
        self._ensure_initialized()

        profile = await patient_service.get_patient_profile(user_id)
        user_name = profile.get("full_name", "there").split()[0] if profile else "there"

        # Build conversation history
        contents = []
        if chat_history:
            for msg in chat_history[-10:]:
                contents.append(types.Content(
                    role="user" if msg["role"] == "user" else "model",
                    parts=[types.Part(text=msg["content"])]
                ))

        contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

        # Prepare function declarations
        function_declarations = self._get_function_declarations()
        tools = [types.Tool(function_declarations=function_declarations)]

        try:
            # Initial request WITHOUT automatic function calling
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self._get_system_instruction(user_name),
                    temperature=0.7,
                    tools=tools
                )
            )

            # Handle function calls manually
            max_iterations = 5
            iteration = 0

            while iteration < max_iterations:
                # Check if response has function calls
                if not response.candidates or not response.candidates[0].content.parts:
                    break

                parts = response.candidates[0].content.parts
                has_function_call = any(hasattr(part, 'function_call') and part.function_call for part in parts)

                if not has_function_call:
                    # No function calls, we have the final text response
                    break

                # Execute all function calls
                function_responses = []
                for part in parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        function_name = fc.name
                        function_args = dict(fc.args) if fc.args else {}

                        # Execute the function
                        try:
                            result = await self._execute_function(user_id, function_name, function_args)
                            function_responses.append(types.Part(
                                function_response=types.FunctionResponse(
                                    name=function_name,
                                    response={"result": result}
                                )
                            ))
                        except Exception as e:
                            print(f"Function execution error ({function_name}): {str(e)}")
                            import traceback
                            traceback.print_exc()
                            function_responses.append(types.Part(
                                function_response=types.FunctionResponse(
                                    name=function_name,
                                    response={"error": str(e)}
                                )
                            ))

                # Add function call and responses to contents
                contents.append(response.candidates[0].content)
                contents.append(types.Content(
                    role="user",
                    parts=function_responses
                ))

                # Get next response
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=self._get_system_instruction(user_name),
                        temperature=0.7,
                        tools=tools
                    )
                )

                iteration += 1

            # Return final text response
            return response.text if response.text else "I'm sorry, I couldn't generate a response."

        except Exception as e:
            print(f"Chatbot error: {str(e)}")
            import traceback
            traceback.print_exc()
            return "I'm sorry, I encountered an error. Please try again."

    async def get_chat_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        result = supabase_admin.table("chat_messages").select("*").eq(
            "user_id", user_id
        ).order("created_at", desc=True).limit(limit).execute()
        return list(reversed(result.data))

    async def save_chat_message(self, user_id: str, role: str, content: str) -> Dict[str, Any]:
        result = supabase_admin.table("chat_messages").insert({
            "user_id": user_id,
            "role": role,
            "content": content,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        return result.data[0] if result.data else None


chatbot_service = ChatbotService()
