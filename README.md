# GenAI Vehicle Diagnostics & Health Monitoring

> **AI-Powered Software Defined Vehicle (SDV) diagnostics** — Real-time telemetry, predictive analytics, multi-language code generation, and MISRA compliance checking for modern vehicles.

---

## Architecture

```
┌──────────────┐    REST/HTTP    ┌──────────────────────────────────────┐
│ Android App  │ ◄────────────► │          FastAPI Backend              │
│ Jetpack      │                │                                      │
│ Compose      │                │  ┌─────────┐  ┌──────────────────┐  │
│              │                │  │Simulator│  │ GenAI Interpreter │  │
└──────────────┘                │  │ Engine  │  │  ├ Code Generator │  │
                                │  └─────────┘  │  ├ Design Gen     │  │
┌──────────────┐                │               │  ├ Test Gen       │  │
│ Web Dashboard│ ◄────────────► │  ┌─────────┐  │  ├ Compliance     │  │
│ (HMI)       │    REST/HTTP    │  │Analytics│  │  └ LLM Comparison │  │
└──────────────┘                │  │ Engine  │  └──────────────────┘  │
                                └──────────────────────────────────────┘
```

---

## Features

### 🔧 Real-Time Vehicle Telemetry
- Speed, battery SoC, tire pressure, engine temperature, odometer, fuel level
- **New**: Throttle, brake, gear position, steering angle, EV range, GPS

### 🤖 GenAI Code Generation Engine
- Multi-language output: **Python**, **C++**, **Kotlin**, **Rust**
- LLM-first approach (Gemini / OpenAI) with template-based fallback
- Design document & test suite generation
- LLM comparison with quality KPIs

### ✅ MISRA C++ Compliance Checking
- Rule-based static analysis for automotive C++ code
- Configurable rule sets (Rule 0-1-1, 2-10-1, 5-0-3, etc.)

### 📊 Predictive Analytics
- Battery depletion estimation
- Tire wear prediction
- Driving score calculation

### 📱 Android App (Jetpack Compose)
- Dark-themed automotive HMI
- Speed gauge, battery indicator, tire pressure grid
- **New**: EV range card, throttle/brake bars, drivetrain panel, GPS display
- **New**: Code Generator screen with language selection
- Bottom navigation: Dashboard → CodeGen → Alerts

### 🖥️ Web Dashboard
- Glassmorphism dark-mode HMI
- Live telemetry, alerts, analytics, code generation
- Vehicle variant selector (EV / Hybrid / ICE)

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

### Docker

```bash
# With optional API key
GOOGLE_API_KEY=your-key docker compose up --build
```

### Android App

Open the `android-app/` folder in Android Studio and run on an emulator or device. Update the backend URL in `RetrofitClient.kt` if needed.

### Web Dashboard

Open `http://localhost:8000/` after starting the backend.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/vehicle/all` | All telemetry data |
| `GET` | `/vehicle/speed` | Speed reading |
| `GET` | `/vehicle/battery` | Battery SoC & health |
| `GET` | `/vehicle/tire-pressure` | Tire pressure (4 tires) |
| `GET` | `/vehicle/alerts` | Active alerts |
| `POST` | `/vehicle/simulate/start` | Start simulator |
| `POST` | `/vehicle/simulate/stop` | Stop simulator |
| `GET` | `/config/signals` | Signal configuration (OTA) |
| `POST` | `/codegen/generate` | Generate code from requirement |
| `GET` | `/codegen/languages` | Supported languages |
| `POST` | `/codegen/design` | Generate design documents |
| `POST` | `/codegen/tests` | Generate test suites |
| `POST` | `/codegen/compare` | Compare LLM providers |
| `POST` | `/compliance/check` | MISRA compliance check |
| `GET` | `/compliance/rules` | Supported MISRA rules |
| `GET` | `/predictive/battery` | Battery depletion forecast |
| `GET` | `/predictive/driving-score` | Driving score |

---

## Project Structure

```
genai-vehicle-diagnostics/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── api/
│   │   ├── vehicle_routes.py    # Telemetry endpoints
│   │   ├── codegen_routes.py    # Code generation endpoints
│   │   └── compliance_routes.py # Compliance endpoints
│   ├── models/telemetry.py      # Pydantic data models
│   ├── simulator/               # Vehicle data simulator
│   └── analytics/               # Health + predictive analytics
├── genai_interpreter/
│   ├── requirement_parser.py    # NLP requirement parsing
│   ├── code_generator.py        # Multi-language code gen
│   ├── design_generator.py      # Design document gen
│   ├── test_generator.py        # Test suite gen
│   ├── compliance_checker.py    # MISRA checker
│   ├── llm_provider.py          # LLM abstraction layer
│   ├── llm_comparison.py        # Provider comparison
│   └── templates/               # Jinja2 fallback templates
├── android-app/                 # Jetpack Compose Android app
├── web-dashboard/               # Static HMI dashboard
├── config/signals_config.json   # OTA signal configuration
├── tests/                       # pytest test suite
├── Dockerfile                   # Container build
├── docker-compose.yml           # Orchestration
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
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_codegen.py -v
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
