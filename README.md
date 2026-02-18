# GenAI Vehicle Diagnostics & Health Monitoring

> **AI-Powered Software Defined Vehicle (SDV) diagnostics** — Real-time telemetry, predictive analytics, ML-based predictions, multi-language code generation, MISRA + AUTOSAR compliance checking, OTA simulation, and WebSocket streaming for modern vehicles.

---

## Architecture

```
┌──────────────┐   REST/WS   ┌─────────────────────────────────────────┐
│ Android App  │ ◄──────────►│           Service-Oriented Backend       │
│ Jetpack      │             │                                         │
│ Compose      │             │  ┌───────────┐  ┌────────────────────┐  │
│              │             │  │ Simulator │  │ GenAI Interpreter  │  │
└──────────────┘             │  │ Engine    │  │  ├ Code Generator  │  │
                              │  │ EV/ICE/   │  │  ├ Design Gen      │  │
┌──────────────┐             │  │ Hybrid    │  │  ├ Test Gen        │  │
│ Web Dashboard│ ◄──────────►│  └───────────┘  │  ├ MISRA Checker   │  │
│ (HMI)       │  REST/WS     │                 │  ├ AUTOSAR Checker │  │
└──────────────┘             │  ┌───────────┐  │  ├ Build Pipeline  │  │
                              │  │ML Engine  │  │  └ LLM Comparison  │  │
                              │  │sklearn RF │  └────────────────────┘  │
                              │  │+ IsoForest│  ┌────────────────────┐  │
                              │  └───────────┘  │ SQLite Persistence │  │
                              │                 └────────────────────┘  │
                              └─────────────────────────────────────────┘
```

---

## Features

### 🔧 Real-Time Vehicle Telemetry
- Speed, battery SoC, tire pressure, engine temperature, odometer, fuel level
- Throttle, brake, gear position, steering angle, EV range, GPS
- **WebSocket** real-time streaming (`/ws/telemetry`) with HTTP polling fallback

### 🤖 GenAI Code Generation Engine
- Multi-language output: **Python**, **C++**, **Kotlin**, **Rust**
- LLM-first approach (Gemini / OpenAI) with template-based fallback
- Design document & test suite generation
- **Iterative build loop**: auto-fix errors via LLM re-generation (up to 3 retries)
- LLM comparison with quality KPIs (`/codegen/demo-compare` — no API key needed)
- Real compilation: g++ (C++), kotlinc (Kotlin), rustc (Rust) when available

### ✅ MISRA + AUTOSAR Compliance Checking
- **15 rules total**: 10 MISRA C++:2008 + 5 AUTOSAR C++ coding guidelines
- MISRA: unreachable code, type casting, magic numbers, uninitialized vars, etc.
- AUTOSAR: RAII enforcement, smart pointers, const correctness, no magic numbers
- ASPICE-aligned compliance level assessment

### 🧠 ML Predictive Analytics (Scikit-Learn)
- Battery depletion prediction (RandomForest)
- Tire wear scoring (RandomForest)
- Anomaly detection (IsolationForest)
- Dashboard ML training controls with status polling

### 📈 Historical Trend Charts
- Chart.js time-series for speed, battery SoC, and tire pressure
- 300-snapshot telemetry history buffer (5 minutes)

### 🚗 Vehicle Variant Simulation
- **EV**: Battery drain, regenerative braking, zero fuel
- **ICE**: Engine-based, fuel consumption, static battery
- **Hybrid**: Dual powertrain, moderate battery drain + fuel

### 📡 OTA Simulation
- Deploy OTA updates via `/ota/deploy`
- Version tracking, deployment history, rollback info

### 🔌 External Simulator Adapter
- CARLA-compatible REST endpoint (`/simulator/external/feed`)
- Schema endpoint for integration guidance

### 💾 Data Persistence
- SQLite-backed telemetry and alert storage (`data/vehicle_diagnostics.db`)
- Data survives server restarts — history auto-loaded on startup

### 📱 Android App (Jetpack Compose)
- Dark-themed automotive HMI
- Speed gauge, battery indicator, tire pressure grid
- EV range card, throttle/brake bars, drivetrain panel, GPS display
- Code Generator screen with language selection
- Bottom navigation: Dashboard → CodeGen → Alerts

### 🖥️ Web Dashboard
- Glassmorphism dark-mode premium HMI
- Live telemetry via WebSocket, alerts, analytics, code generation
- ML Training tab, OTA Updates tab, Trend Charts
- Vehicle variant selector (EV / Hybrid / ICE)

### 🐳 SoA Docker Architecture
- 4 separate services: telemetry, codegen, ml, dashboard (nginx)
- Health checks, service dependencies, isolated scaling

---

## Quick Start

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# (Optional) Set LLM API keys for GenAI features
export GOOGLE_API_KEY="your-gemini-key"
```

### Docker (SoA)

```bash
# With optional API key
GOOGLE_API_KEY=your-key docker compose up --build
```

### Android App

Open the `android-app/` folder in Android Studio and run on an emulator or device. Update the backend URL in `RetrofitClient.kt` if needed.

### Web Dashboard

Open `http://localhost:8000/dashboard` after starting the backend.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/vehicle/all` | All telemetry data |
| `GET` | `/vehicle/speed` | Speed reading |
| `GET` | `/vehicle/battery` | Battery SoC & health |
| `GET` | `/vehicle/tire-pressure` | Tire pressure (4 tires) |
| `GET` | `/vehicle/alerts` | Active alerts |
| `GET` | `/vehicle/history` | Telemetry history (trend charts) |
| `POST` | `/vehicle/simulate/start` | Start simulator (?variant=EV/ICE/Hybrid) |
| `POST` | `/vehicle/simulate/stop` | Stop simulator |
| `WS` | `/ws/telemetry` | Real-time WebSocket telemetry stream |
| `GET` | `/config/signals` | Signal configuration (OTA) |
| `POST` | `/codegen/generate` | Generate code from requirement |
| `POST` | `/codegen/validate` | Validate + iterative auto-fix |
| `POST` | `/codegen/build` | Build/compile check |
| `GET` | `/codegen/demo-compare` | Demo LLM comparison (no key needed) |
| `POST` | `/compliance/check` | MISRA + AUTOSAR compliance check |
| `GET` | `/compliance/rules` | Supported rules (15 total) |
| `POST` | `/ml/train` | Train ML models |
| `POST` | `/ml/predict` | Run ML predictions |
| `GET` | `/ml/status` | Training status |
| `POST` | `/ota/deploy` | Deploy OTA update |
| `GET` | `/ota/history` | OTA deployment history |
| `POST` | `/simulator/external/feed` | Feed external simulator data |
| `GET` | `/predictive/analysis` | Predictive analytics |

---

## Project Structure

```
genai-vehicle-diagnostics/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── api/
│   │   ├── vehicle_routes.py    # Telemetry endpoints
│   │   ├── simulation_routes.py # Sim control
│   │   ├── codegen_routes.py    # Code generation + demo-compare
│   │   ├── compliance_routes.py # MISRA + AUTOSAR compliance
│   │   ├── ml_routes.py         # ML train/predict
│   │   ├── ota_routes.py        # OTA deploy/history
│   │   ├── history_routes.py    # Telemetry history
│   │   ├── ws_routes.py         # WebSocket streaming
│   │   └── external_sim_routes.py # CARLA adapter
│   ├── ml/
│   │   ├── ml_trainer.py        # Scikit-Learn model training
│   │   └── ml_predictor.py      # Inference engine
│   ├── models/telemetry.py      # Pydantic data models
│   ├── simulator/               # Variant-aware vehicle simulator
│   ├── services/
│   │   ├── data_store.py        # In-memory state + persistence
│   │   └── persistence.py       # SQLite persistence layer
│   └── analytics/               # Health + predictive analytics
├── genai_interpreter/
│   ├── requirement_parser.py    # NLP requirement parsing
│   ├── code_generator.py        # Multi-language code gen
│   ├── design_generator.py      # Design document gen
│   ├── test_generator.py        # Test suite gen
│   ├── compliance_checker.py    # MISRA + AUTOSAR checker (15 rules)
│   ├── build_pipeline.py        # Multi-lang compile (g++/kotlinc/rustc)
│   ├── llm_provider.py          # LLM abstraction layer
│   ├── llm_comparison.py        # Provider comparison engine
│   └── templates/               # Jinja2 fallback templates
├── android-app/                 # Jetpack Compose Android app
├── web-dashboard/               # HMI dashboard (HTML/CSS/JS)
├── data/                        # SQLite database (auto-created)
├── config/signals_config.json   # OTA signal configuration
├── tests/                       # pytest test suite (7 files)
├── Dockerfile                   # Container build
├── docker-compose.yml           # SoA orchestration (4 services)
└── .github/workflows/ci.yml    # CI pipeline
```

---

## Vehicle Signals (12 total)

| Signal | Unit | Range | UI Widget |
|--------|------|-------|-----------|
| Speed | km/h | 0–240 | Gauge |
| Battery SoC | % | 0–100 | Bar |
| Tire Pressure | psi | 0–50 | Grid (4) |
| Engine Temp | °C | 0–150 | Gauge |
| Fuel Level | % | 0–100 | Bar |
| Odometer | km | 0–999999 | Display |
| Throttle | % | 0–100 | Bar |
| Brake | % | 0–100 | Bar |
| Gear | – | P/R/N/D/1–6 | Indicator |
| Steering | ° | -540–540 | Wheel |
| EV Range | km | 0–800 | Display |
| GPS | lat/lon | – | Map |

---

## Testing

```bash
# Run all tests (7 test files, 60+ test cases)
pytest tests/ -v

# Run specific test suites
pytest tests/test_ml.py -v          # ML training + prediction
pytest tests/test_compliance.py -v  # MISRA + AUTOSAR rules
pytest tests/test_simulator.py -v   # Variant-aware simulator
pytest tests/test_api.py -v         # API integration tests
```

---

## CI/CD

GitHub Actions pipeline runs on every push to `main`/`develop`:
1. Install Python 3.11 + dependencies
2. Run `pytest tests/ -v`
3. Lint with flake8 (non-blocking)
4. Build Docker image (main branch only)

---

## License

This project is for educational and demonstration purposes.
