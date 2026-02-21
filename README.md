# GenAI Vehicle Diagnostics & Health Monitoring
Team AaVaRa - Tata Elxsi Teliport Season 3 (Case Study 2)

> **AI-Powered Software Defined Vehicle (SDV) diagnostics** — Real-time telemetry, predictive analytics, ML-based predictions, multi-language code generation, MISRA + AUTOSAR compliance checking, OTA simulation, and WebSocket streaming for modern vehicles.

---

## 🏗️ Architecture

```
┌──────────────┐   REST/WS   ┌─────────────────────────────────────────┐
│ Android App  │ ◄──────────►│           Service-Oriented Backend       │
│ Jetpack      │             │                                         │
│ Compose      │             │  ┌───────────┐  ┌────────────────────┐  │
│              │             │  │ Simulator │  │ GenAI Interpreter  │  │
└──────────────┘             │  │ Engine    │  │  ├ Code Generator  │  │
                             │  │ EV/ICE/   │  │  ├ Design Gen      │  │
┌──────────────┐             │  │ Hybrid    │  │  ├ Test Gen        │  │
│ Web Dashboard│ ◄──────────►│  └───────────┘  │  ├ MISRA/AUTOSAR   │  │
│ (HMI)        │  REST/WS    │                 │  ├ Iterative Build │  │
└──────────────┘             │  ┌───────────┐  │  └ OTA Deployment  │  │
                             │  │ML Engine  │  └────────────────────┘  │
                             │  │sklearn RF │  ┌────────────────────┐  │
                             │  │+ IsoForest│  │ SQLite Persistence │  │
                             │  └───────────┘  └────────────────────┘  │
                             └─────────────────────────────────────────┘
```

---

## ✨ Features

### 🔧 Real-Time Vehicle Telemetry Simulator
- **Vehicle Variants:** Simulates physics and battery drain for **EV**, **Hybrid**, and **ICE** configurations.
- **Signals:** Speed, battery SoC, tire pressure, drivetrain attributes (throttle, brake, gear, steering), GPS coordinates, and more.
- **External Simulator Ready:** Designed to seamlessly ingest high-frequency telemetry from external industry-standard tools like **CARLA** or **CarMaker** via `UDP`, `WebSockets`, and `REST API`. Includes a demo script (`demo_external_sim.py`) to prove real-time ingestion capabilities. 
- **Streaming:** **WebSocket** real-time streaming (`/ws/telemetry`) with HTTP polling fallback.

### 🤖 GenAI Code Generation & Iterative Pipeline
- **Multi-language output**: Generates **Python**, **C++**, **Kotlin**, and **Rust** directly from natural language diagnostics requirements.
- **Iterative Build & Auto-Fixing Pipeline:** Generates code, automatically generates a testing suite, executes the tests against the generated code, and utilizes the LLM to auto-fix failing code (up to 3 retries) until it passes.
- **Build Checks:** Real compilation checks via `g++` (C++), `kotlinc` (Kotlin), and `rustc` (Rust).
- **Design & Tests:** Generates distinct Software Design Documents and standalone Unit Tests based on constraints.

### 🚀 Edge OTA Code Deployment
- Simulates Edge OTA deployment directly from the Code Generation loop.
- One-click **"Deploy via OTA"** immediately pushes generated, validated code models to the simulated edge vehicle (`deployed_modules/` folder).
- Maintains a strict historical registry of deployed configurations, tracked via the Dashboard.

### ✅ MISRA + AUTOSAR Compliance Verification
- **15 Integrated Rules**: Deep compliance analysis against 10 **MISRA C++:2008** and 5 **AUTOSAR C++** coding guidelines.
- Checks coverage for: Unreachable code, magic numbers, type casting safety, uninitialized variables, RAII enforcement, and smart pointers.
- Provides ASPICE-aligned compliance percentage and line-by-line violation reports.

### 🧠 Predictive Analytics & Machine Learning
- Built on top of `scikit-learn`.
- **Battery Depletion Prediction:** Estimates remaining minutes via RandomForest Regressors.
- **Tire Wear Scoring:** Evaluates real-time wear via RandomForest Classifiers.
- **Anomaly Detection:** Identifies abnormal telemetry sequences using IsolationForest.
- Dedicated ML Training tab in the dashboard to generate samples and dynamically train the models at runtime.

### 📈 Dynamic Analytics Dashboard (HMI)
- Beautiful glassmorphism dark-mode Vanilla JS/HTML5 Web Dashboard.
- **Trend Charts:** Uses `Chart.js` for historical time-series data of speed, battery, and 4-wheel tire pressures.
- **Driving Score:** Real-time gamified scoring of braking, accelerating, and efficiency algorithms.
- **Live Alerts Engine:** Translates anomalous conditions into flashing UI notifications with severity levels.

### 💾 Scalable Persistence
- SQLite-backed telemetry and alert storage (`data/vehicle_diagnostics.db`).
- Auto-rehydrates telemetry from disk over long durations so the dashboard trend charts survive server restarts.

---

## 🚦 Quick Start

### Backend (Local Python)

```bash
# Install dependencies
pip install -r requirements.txt

# Start the uvicorn API server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# (Optional) Export LLM API keys for advanced GenAI features
export GOOGLE_API_KEY="your-gemini-key"

# OR run the fully containerized stack via Docker
docker-compose up --build
```

### Web Dashboard

After starting the backend, open your browser and navigate to:
👉 `http://localhost:8000/dashboard`

### Android App

For taking the dashboard on the go: 
1. Open the `android-app/` folder in Android Studio.
2. Ensure you have the latest Gradle build tools installed.
3. Update the backend URL in `RetrofitClient.kt` if running on a physical device over a network.
4. Run on an emulator.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/vehicle/all` | All telemetry data |
| `GET` | `/vehicle/speed` | Speed reading |
| `GET` | `/vehicle/history` | Telemetry history (trend charts) |
| `POST` | `/vehicle/simulate/start` | Start simulator (`?variant=EV/ICE/Hybrid`) |
| `WS` | `/ws/telemetry` | Real-time WebSocket telemetry stream |
| `POST` | `/codegen/generate` | Generate code from requirement |
| `POST` | `/codegen/validate` | **Validate + iterative test/auto-fix loop** |
| `POST` | `/codegen/build` | Build and compile check (syntax verification) |
| `POST` | `/compliance/check` | MISRA + AUTOSAR compliance check |
| `POST` | `/ml/train` | Train ML models based on recent vehicle data |
| `POST` | `/ml/predict` | Run ML predictions on current snapshot |
| `POST` | `/ota/deploy` | **Deploy OTA update (configuration or code module)** |
| `GET` | `/ota/history` | OTA deployment history |

---

## 🗂️ Project Structure

```
genai-vehicle-diagnostics/
├── backend/
│   ├── main.py                  # FastAPI server entry point
│   ├── api/                     # REST / WebSocket endpoints
│   ├── ml/                      # Scikit-Learn training and inference
│   ├── models/                  # Pydantic data models
│   ├── simulator/               # EV/ICE/Hybrid background simulator
│   └── services/                # In-memory singleton states and SQLite persistence
├── genai_interpreter/
│   ├── code_generator.py        # Abstract multi-lang LLM generator
│   ├── compliance_checker.py    # MISRA + AUTOSAR rule validator
│   ├── build_pipeline.py        # Real-time C++/Rust/Kotlin compiler hooks
│   ├── test_generator.py        # Auto-generation of Unit Tests
│   └── templates/               # Fallback code templates (zero-auth mode)
├── android-app/                 # Jetpack Compose Kotlin HMI
├── web-dashboard/               # HTML/CSS/JS glassmorphism dashboard
├── config/                      # JSON-based simulated signal configurations
├── tests/                       # Complete pytest suite
└── deployed_modules/            # Folder populated dynamically by Node OTA Deployments
```

---

## 🧪 Testing

The repository features comprehensive integration and unit tests passing at 100%. Ensure the backend is not actively running `uvicorn` during stateful tests to avoid socket collisions.

```bash
# Run all tests (API, ML, compliance, simulators)
pytest tests/ -v
```

---

## 📄 License

This project was built for educational and demonstration purposes.
