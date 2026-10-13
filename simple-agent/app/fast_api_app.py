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

import contextlib
import os
from collections.abc import AsyncIterator
from typing import Optional

from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner
from pydantic import BaseModel

from app.app_utils import services
from app.app_utils.a2a import attach_a2a_routes
from app.agent import validate_and_get_user_details, get_hyderabad_weather_and_outdoor_activity

load_dotenv()
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.agent import app as adk_app
    from app.agent import root_agent

    runner = Runner(
        app=adk_app,
        session_service=services.get_session_service(),
        artifact_service=services.get_artifact_service(),
        auto_create_session=True,
    )
    app.state.runner = runner
    app.state.agent_app_name = adk_app.name
    await attach_a2a_routes(
        app,
        agent=root_agent,
        runner=runner,
        task_store=InMemoryTaskStore(),
        rpc_path=f"/a2a/{adk_app.name}",
    )
    yield


app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=services.ARTIFACT_SERVICE_URI,
    allow_origins=allow_origins,
    session_service_uri=services.SESSION_SERVICE_URI,
    otel_to_cloud=True,
    lifespan=lifespan,
)
app.title = "simple-agent"
app.description = "API for interacting with the Agent simple-agent"


class ValidateRequest(BaseModel):
    name: str


@app.post("/api/validate-user")
async def api_validate_user(payload: ValidateRequest):
    user_name = payload.name.strip()
    val_res = validate_and_get_user_details(user_name)
    age = None
    if val_res.get("valid"):
        age = val_res.get("record", {}).get("age")
    weather_res = get_hyderabad_weather_and_outdoor_activity(age=age)

    if not val_res.get("valid"):
        return JSONResponse(
            status_code=404,
            content={
                "valid": False,
                "message": f"User '{user_name}' could not be validated in the database.",
                "weather": weather_res,
                "bg_color": "#FEE2E2",  # Light red for not found
            },
        )

    record = val_res.get("record", {})
    age = record.get("age", 0)
    bg_color_raw = record.get("bg_color", "").lower()

    # Determine background styling
    # Age group mapping & color styling
    color_map = {
        "baby pink": "#FBCFE8",    # 10 years / kids
        "pink": "#FBCFE8",
        "light blue": "#BAE6FD",   # 60 years / seniors
        "blue": "#BAE6FD",
        "light yellow": "#FEF08A", # 30 years / young adults
        "yellow": "#FEF08A",
    }
    hex_color = color_map.get(bg_color_raw)
    if not hex_color:
        if age <= 18:
            hex_color = "#FBCFE8"
        elif age >= 50:
            hex_color = "#BAE6FD"
        else:
            hex_color = "#FEF08A"

    return {
        "valid": True,
        "record": record,
        "suggestion": record.get("suggestion", ""),
        "bg_color_name": record.get("bg_color", ""),
        "bg_color_hex": hex_color,
        "weather": weather_res,
    }


@app.get("/ui", response_class=HTMLResponse)
async def serve_ui():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User Validation & Weather Agent Interface</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            box-sizing: border-box;
            transition: background-color 0.4s ease, border-color 0.3s ease;
        }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 40px 20px;
            background-color: #F8FAFC;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            width: 100%;
            max-width: 650px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(8px);
            padding: 36px 32px;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);
            border: 1px solid rgba(226, 232, 240, 0.8);
        }
        h1 {
            font-size: 24px;
            font-weight: 700;
            color: #0F172A;
            margin-top: 0;
            margin-bottom: 8px;
            text-align: center;
        }
        p.subtitle {
            font-size: 14px;
            color: #64748B;
            text-align: center;
            margin-bottom: 28px;
        }
        .sample-badges {
            display: flex;
            justify-content: center;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 24px;
        }
        .sample-chip {
            background: #F1F5F9;
            border: 1px solid #E2E8F0;
            padding: 5px 12px;
            border-radius: 9999px;
            font-size: 12px;
            color: #334155;
            cursor: pointer;
            user-select: none;
        }
        .sample-chip:hover {
            background: #E2E8F0;
        }
        .input-group {
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
        }
        input[type="text"] {
            flex: 1;
            padding: 14px 18px;
            font-size: 15px;
            border: 2px solid #CBD5E1;
            border-radius: 12px;
            outline: none;
            color: #1E293B;
            background: #FFFFFF;
        }
        input[type="text"]:focus {
            border-color: #3B82F6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
        }
        button {
            padding: 14px 26px;
            font-size: 15px;
            font-weight: 600;
            color: #FFFFFF;
            background: #2563EB;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
        }
        button:hover {
            background: #1D4ED8;
        }
        button:disabled {
            background: #94A3B8;
            cursor: not-allowed;
            box-shadow: none;
        }
        .result-card {
            display: none;
            margin-top: 24px;
            padding: 24px;
            border-radius: 16px;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
        }
        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.06);
        }
        .card-title {
            font-size: 18px;
            font-weight: 700;
            color: #0F172A;
        }
        .status-pill {
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-valid {
            background: #DCFCE7;
            color: #15803D;
        }
        .status-invalid {
            background: #FEE2E2;
            color: #B91C1C;
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 16px;
            font-size: 14px;
        }
        .label {
            color: #64748B;
            font-weight: 500;
        }
        .value {
            color: #0F172A;
            font-weight: 600;
        }
        .box {
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            padding: 14px 16px;
            border-radius: 12px;
            margin-bottom: 12px;
            font-size: 14px;
        }
        .box-title {
            font-weight: 700;
            margin-bottom: 4px;
            color: #334155;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .loading {
            text-align: center;
            color: #64748B;
            font-size: 14px;
            display: none;
            padding: 12px;
        }
    </style>
</head>
<body>
    <div class="container" id="mainContainer">
        <h1>Agent Profile & Weather Validator</h1>
        <p class="subtitle">Validates user profile in Firestore memory bank & suggests Hyderabad outdoor activities</p>

        <div class="sample-badges">
            <span class="sample-chip" onclick="fillInput('kids')">Demo: kids (10y)</span>
            <span class="sample-chip" onclick="fillInput('parents')">Demo: parents (30y)</span>
            <span class="sample-chip" onclick="fillInput('grand parents')">Demo: grand parents (60y)</span>
        </div>

        <div class="input-group">
            <input type="text" id="nameInput" placeholder="Enter user name (e.g., first1 last1)" autocomplete="off">
            <button id="submitBtn" onclick="validateUser()">Submit</button>
        </div>

        <div class="loading" id="loadingSpinner">Validating profile with agent and checking Hyderabad weather...</div>

        <div class="result-card" id="resultCard">
            <div class="card-header">
                <span class="card-title" id="cardName">User Profile</span>
                <span class="status-pill" id="statusPill">Validated</span>
            </div>

            <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 12px;" id="profileHeader">
                <img id="valPhoto" src="" alt="Cartoon Avatar" style="display: none; width: 80px; height: 80px; border-radius: 12px; object-fit: cover; border: 2px solid #CBD5E1; box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
                <div class="grid" id="detailsGrid" style="grid-template-columns: 1fr 1fr; flex: 1; margin-bottom: 0;">
                    <div><span class="label">Name: </span><span class="value" id="valName">-</span></div>
                    <div><span class="label">Age: </span><span class="value" id="valAge">-</span></div>
                </div>
            </div>

            <div class="box" id="suggestionBox" style="transition: all 0.3s ease;">
                <div class="box-title">💡 Database Suggestion:</div>
                <div id="suggestionText">-</div>
            </div>

            <div class="box" id="weatherBox">
                <div class="box-title">🌤️ Current Hyderabad Weather & Outdoor Activity:</div>
                <ul id="weatherPoints" style="margin: 8px 0 0 16px; padding: 0; line-height: 1.6; font-size: 13.5px; color: #1E293B;">
                    <li><strong>Location:</strong> Hyderabad, India</li>
                    <li><strong>Condition:</strong> <span id="wCondition">-</span></li>
                    <li><strong>Temperature:</strong> <span id="wTemp">-</span></li>
                    <li><strong>Humidity:</strong> <span id="wHumidity">-</span></li>
                    <li><strong>Outdoor Activity:</strong> <span id="wActivity" style="font-weight: 500;">-</span></li>
                </ul>
            </div>
        </div>
    </div>

    <script>
        function fillInput(val) {
            document.getElementById('nameInput').value = val;
            validateUser();
        }

        async function validateUser() {
            const name = document.getElementById('nameInput').value.trim();
            if (!name) return;

            const submitBtn = document.getElementById('submitBtn');
            const loading = document.getElementById('loadingSpinner');
            const card = document.getElementById('resultCard');
            const container = document.getElementById('mainContainer');
            const suggestionBox = document.getElementById('suggestionBox');

            submitBtn.disabled = true;
            loading.style.display = 'block';
            card.style.display = 'none';

            try {
                const res = await fetch('/api/validate-user', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name: name})
                });
                const data = await res.json();

                card.style.display = 'block';
                if (data.valid) {
                    const rec = data.record;
                    // Apply designated bg_color to Database Suggestion box
                    const bgColor = data.bg_color_hex || '#FEF08A';
                    suggestionBox.style.backgroundColor = bgColor;
                    suggestionBox.style.borderColor = 'rgba(0,0,0,0.15)';
                    suggestionBox.style.color = '#0F172A';

                    document.getElementById('cardName').innerText = rec.name;
                    document.getElementById('statusPill').className = 'status-pill status-valid';
                    document.getElementById('statusPill').innerText = 'Verified in DB';

                    // Show ONLY name, age, and cartoon photo
                    document.getElementById('valName').innerText = rec.name;
                    document.getElementById('valAge').innerText = (rec.age || '-') + ' years';

                    const photoEl = document.getElementById('valPhoto');
                    if (rec.photo) {
                        photoEl.src = rec.photo;
                        photoEl.style.display = 'block';
                    } else {
                        photoEl.style.display = 'none';
                    }

                    document.getElementById('suggestionText').innerText = data.suggestion;

                    const w = data.weather;
                    document.getElementById('wCondition').innerText = w.condition;
                    document.getElementById('wTemp').innerText = `${w.temperature_celsius}°C`;
                    document.getElementById('wHumidity').innerText = `${w.humidity_percent}%`;
                    document.getElementById('wActivity').innerText = w.suggested_activity;
                    document.getElementById('detailsGrid').style.display = 'grid';
                } else {
                    suggestionBox.style.backgroundColor = '#FEE2E2';
                    suggestionBox.style.borderColor = '#FCA5A5';
                    suggestionBox.style.color = '#991B1B';

                    document.getElementById('cardName').innerText = name;
                    document.getElementById('statusPill').className = 'status-pill status-invalid';
                    document.getElementById('statusPill').innerText = 'Not Found';

                    document.getElementById('detailsGrid').style.display = 'none';
                    document.getElementById('suggestionText').innerText = data.message;

                    const w = data.weather;
                    document.getElementById('wCondition').innerText = w.condition;
                    document.getElementById('wTemp').innerText = `${w.temperature_celsius}°C`;
                    document.getElementById('wHumidity').innerText = `${w.humidity_percent || '-'}%`;
                    document.getElementById('wActivity').innerText = w.suggested_activity;
                }
            } catch (err) {
                alert('Request failed: ' + err);
            } finally {
                submitBtn.disabled = false;
                loading.style.display = 'none';
            }
        }

        document.getElementById('nameInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') validateUser();
        });
    </script>
</body>
</html>
"""


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
