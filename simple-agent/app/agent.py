# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import re
import urllib.request
from typing import Any, Dict, Optional
from google.cloud import firestore

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.genai import types

MODEL = "gemini-2.5-flash"
PROJECT_ID = "qwiklabs-gcp-04-d5a16181d919"  # Hardcoded string as requested
DATABASE_NAME = "my-db"
COLLECTION_NAME = "my_details"


def get_firestore_client() -> firestore.Client:
    """Returns a Firestore client configured with hardcoded project ID and database."""
    return firestore.Client(project=PROJECT_ID, database=DATABASE_NAME)


def validate_and_get_user_details(name: str) -> Dict[str, Any]:
    """Queries the Firestore 'my_details' table to validate against an input user name.

    Args:
        name: Name of the person to validate against the database.

    Returns:
        A dictionary with validation status and user record (name, govt_id, age,
        allow_social_media, suggestion, bg_color, photo).
    """
    client = get_firestore_client()
    clean_name = name.strip()
    doc_id = clean_name.lower().replace(" ", "_")

    # Direct document lookup
    doc = client.collection(COLLECTION_NAME).document(doc_id).get()
    if doc.exists:
        data = doc.to_dict() or {}
        return {"valid": True, "record": data}

    # Case-insensitive / whitespace-tolerant lookup across collection
    for d in client.collection(COLLECTION_NAME).stream():
        rec = d.to_dict()
        if rec.get("name", "").strip().lower() == clean_name.lower():
            return {"valid": True, "record": rec}

    return {
        "valid": False,
        "message": f"User '{clean_name}' was not found in the my_details database.",
    }


def get_hyderabad_weather_and_outdoor_activity(age: Optional[int] = None) -> Dict[str, Any]:
    """Gets the current real-time weather in Hyderabad, India and suggests an outdoor
    activity specifically customized to the user's age group and current weather conditions.

    Args:
        age: The age of the person (optional). Used to tailor outdoor activities
             specifically for kids (~10 years), young adults (~30 years), or seniors (~60 years).

    Returns:
        A dictionary containing weather conditions (temperature, humidity, description)
        and an age-tailored outdoor activity recommendation.
    """
    lat, lon = 17.3850, 78.4867
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Agent-Weather/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            current = data.get("current", {})
            temp_c = current.get("temperature_2m", 30.0)
            humidity = current.get("relative_humidity_2m", 40)
            weather_code = current.get("weather_code", 0)

            if weather_code == 0:
                condition = "Clear / Sunny sky"
            elif weather_code in [1, 2, 3]:
                condition = "Partly cloudy"
            elif weather_code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
                condition = "Rainy / Showers"
            elif weather_code in [95, 96, 99]:
                condition = "Thunderstorm"
            else:
                condition = "Moderate weather"

            # Age-specific outdoor activity suggestions
            if age is not None and age <= 18:
                # Children / Kids (~10 years)
                if "Rain" in condition or "Thunder" in condition:
                    activity = (
                        "For kids (approx 10 yrs): Rainy outdoors! Best to visit Birla Science Museum & Planetarium "
                        "or take the sheltered lion safari ride at Nehru Zoological Park."
                    )
                elif temp_c > 34:
                    activity = (
                        "For kids (approx 10 yrs): It's sunny and warm! Enjoy afternoon fun at Jalavihar Water Park, "
                        "followed by a sunset boat ride at Lumbini Park."
                    )
                else:
                    activity = (
                        "For kids (approx 10 yrs): Great outdoor weather! Perfect for cycling around Sanjeevaiah Park, "
                        "flying kites, or exploring the adventure play area at Jalavihar."
                    )
            elif age is not None and age >= 50:
                # Seniors (~60 years)
                if "Rain" in condition or "Thunder" in condition:
                    activity = (
                        "For seniors (approx 60 yrs): Wet pathways outside. Recommended peaceful visit to Birla Mandir "
                        "or a cultural stroll through Salar Jung Museum."
                    )
                elif temp_c > 34:
                    activity = (
                        "For seniors (approx 60 yrs): Warm outside. Take a gentle, shaded early morning walk at KBR National Park "
                        "or relax by the shaded benches at Lotus Pond during cooler hours."
                    )
                else:
                    activity = (
                        "For seniors (approx 60 yrs): Wonderful mild weather! Ideal for a relaxing, low-impact evening stroll "
                        "around Lotus Pond or tranquil garden walk at Qutb Shahi Tombs."
                    )
            else:
                # Young Adults / Adults (~30 years)
                if "Rain" in condition or "Thunder" in condition:
                    activity = (
                        "For young adults (approx 30 yrs): Rainy conditions! Relax at cozy rooftop cafes in Jubilee Hills "
                        "or explore the covered arts and crafts pavilions at Shilparamam."
                    )
                elif temp_c > 34:
                    activity = (
                        "For young adults (approx 30 yrs): Warm afternoon. Plan an evening jog across Durgam Cheruvu cable bridge "
                        "or rock bouldering at Khajaguda Hills as the sun goes down."
                    )
                else:
                    activity = (
                        "For young adults (approx 30 yrs): Prime outdoor conditions! Great for trekking the ramparts of Golconda Fort, "
                        "cycling the Gandipet track, or hiking at Khajaguda Hills."
                    )

            return {
                "city": "Hyderabad, India",
                "temperature_celsius": temp_c,
                "humidity_percent": humidity,
                "condition": condition,
                "target_age": age,
                "suggested_activity": activity,
            }
    except Exception as e:
        if age is not None and age <= 18:
            activity = "For kids: Enjoy visiting Nehru Zoological Park or the children's park at Lumbini Park."
        elif age is not None and age >= 50:
            activity = "For seniors: Take a gentle evening walk at Lotus Pond or KBR National Park."
        else:
            activity = "For young adults: Great time for an evening run at Durgam Cheruvu cable bridge or exploring Golconda Fort."

        return {
            "city": "Hyderabad, India",
            "temperature_celsius": 32.0,
            "condition": "Sunny",
            "target_age": age,
            "suggested_activity": activity,
            "error_note": str(e),
        }


# AgentEngineSandboxCodeExecutor configuration
# If deployment_metadata.json or env vars supply a sandbox or agent engine resource name, use it;
# otherwise AgentEngineSandboxCodeExecutor will auto-create or use project/location defaults.
sandbox_resource_name = os.getenv("SANDBOX_RESOURCE_NAME")
agent_engine_resource_name = os.getenv("AGENT_ENGINE_RESOURCE_NAME")

# Also check deployment_metadata.json if present
deployment_metadata_file = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deployment_metadata.json"
)
if os.path.exists(deployment_metadata_file):
    try:
        with open(deployment_metadata_file, "r") as f:
            metadata = json.load(f)
            if not sandbox_resource_name:
                sandbox_resource_name = metadata.get("sandbox_resource_name")
            if not agent_engine_resource_name:
                agent_engine_resource_name = metadata.get("agent_engine_resource_name") or metadata.get("resource_name")
    except Exception:
        pass

code_executor_kwargs = {}
sandbox_pattern = r"^projects/([a-zA-Z0-9-_]+)/locations/([a-zA-Z0-9-_]+)/reasoningEngines/(\d+)/sandboxEnvironments/(\d+)$"
agent_engine_pattern = r"^projects/([a-zA-Z0-9-_]+)/locations/([a-zA-Z0-9-_]+)/reasoningEngines/(\d+)$"

if sandbox_resource_name and re.fullmatch(sandbox_pattern, sandbox_resource_name):
    code_executor_kwargs["sandbox_resource_name"] = sandbox_resource_name
elif agent_engine_resource_name and re.fullmatch(agent_engine_pattern, agent_engine_resource_name):
    code_executor_kwargs["agent_engine_resource_name"] = agent_engine_resource_name

code_executor = AgentEngineSandboxCodeExecutor(**code_executor_kwargs)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are an assistant that validates user profiles and provides age-tailored recommendations. "
        "Note: The literal user names stored in the database include 'kids', 'parents', and 'grand parents'. When a user asks to validate 'kids', 'parents', or 'grand parents', treat those as exact user names and immediately call the validation tool. "
        "When given a user's name: "
        "1. Call validate_and_get_user_details(name) to check if the user exists in the Firestore database. "
        "2. From the validation result, note the user's age and cartoon photo URL. "
        "3. Call get_hyderabad_weather_and_outdoor_activity(age=...) passing the user's exact age so the outdoor activity is specifically tailored to their age group (kids/10y, young adults/30y, or seniors/60y) rather than being identical for everyone. "
        "4. Provide a focused response containing: "
        "   - Cartoon Profile Image: If the record contains a 'photo' URL, always display it nicely at the top of the profile using markdown: ![Cartoon Profile Photo](<photo_url>) "
        "   - Uncluttered Profile Points: "
        "     * **Name:** <user name> "
        "     * **Age:** <user age> "
        "     * **Database Suggestion:** **<db suggestion>** (styled or highlighted with their profile's bg_color: baby pink, light blue, or light yellow) "
        "   (Do NOT output govt_id or allow_social_media). "
        "   - Current Hyderabad Weather & Outdoor Activity section uncluttered and formatted as clean, concise bullet points: "
        "     * **Location:** Hyderabad, India "
        "     * **Condition:** <weather condition> "
        "     * **Temperature:** <temp>°C "
        "     * **Humidity:** <humidity>% "
        "     * **Outdoor Activity:** <tailored activity recommendation> "
        "Do not write long rambling paragraphs; keep both the profile info and the weather section strictly to these clean bullet points. "
        "If the user is not found, politely report that they are not in the database and state that access could not be validated. "
        "You also have Python code execution enabled via a secure sandbox to run calculations, data manipulation, or code when needed."
    ),
    tools=[
        validate_and_get_user_details,
        get_hyderabad_weather_and_outdoor_activity,
    ],
    code_executor=code_executor,
)

app = App(
    root_agent=root_agent,
    name="app",
)
