"""
Design Document Generator.

Generates service interface design documents from parsed requirement blueprints:
- API contract specifications (OpenAPI-style)
- Data flow descriptions
- Class/component diagrams (Mermaid)
- Architecture overview
"""

import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from genai_interpreter.llm_provider import get_provider, record_metrics, LLMCallMetrics

logger = logging.getLogger(__name__)


@dataclass
class DesignDocument:
    """Generated design document."""
    title: str
    content: str
    format: str  # "markdown"
    generation_method: str  # "template" or "llm:<provider>"
    generation_time_ms: float
    llm_metrics: Optional[LLMCallMetrics] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Template-based design generation ─────────────────────────────────────────

def _generate_design_from_template(blueprint: Dict[str, Any]) -> str:
    """Build design doc using structured templates."""
    req = blueprint.get("raw_requirement", "N/A")
    signals = blueprint.get("signals", [])
    services = blueprint.get("services", [])
    ui_components = blueprint.get("ui_components", [])
    alerts = blueprint.get("alerts", [])

    signal_list = "\n".join(f"  - `{s}`" for s in signals) or "  - (none)"
    service_list = "\n".join(f"  - `{s}`" for s in services) or "  - (none)"
    ui_list = "\n".join(f"  - `{u}`" for u in ui_components) or "  - (none)"
    alert_list = "\n".join(f"  - `{a}`" for a in alerts) or "  - (none)"

    # API contract section
    api_rows = ""
    for sig in signals:
        endpoint = sig.replace("_", "-")
        api_rows += f"| `GET` | `/vehicle/{endpoint}` | Current {sig.replace('_', ' ')} data | `{sig}` value, unit, status |\n"
    api_rows += "| `GET` | `/vehicle/all` | Complete telemetry snapshot | All signal values |\n"
    api_rows += "| `GET` | `/vehicle/alerts` | Active alerts & warnings | List of alert objects |\n"
    api_rows += "| `POST` | `/vehicle/simulate/start` | Start data simulation | Simulation status |\n"
    api_rows += "| `POST` | `/vehicle/simulate/stop` | Stop data simulation | Simulation status |\n"

    # Mermaid class diagram
    signal_attrs = "\n".join(f"        +float {s}" for s in signals)
    service_methods = "\n".join(f"        +get_{s}() {s.title().replace('_','')}Data" for s in signals)
    ui_boxes = "\n".join(f"    VehicleService --> {u.replace('_', '')}" for u in ui_components)

    doc = f"""# Service Interface Design Document

## 1. Requirement

> {req}

## 2. Extracted Components

### Signals
{signal_list}

### Services
{service_list}

### UI Components
{ui_list}

### Alert Types
{alert_list}

---

## 3. API Contract

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
{api_rows}

### Data Models

#### VehicleTelemetry
```json
{{
  "timestamp": "ISO-8601",
{chr(10).join(f'  "{s}": {{"value": 0.0, "unit": "...", "status": "normal"}},' for s in signals)}
  "engine_status": "running"
}}
```

#### Alert
```json
{{
  "id": "uuid",
  "alert_type": "string",
  "severity": "info | warning | critical",
  "message": "Human-readable description",
  "signal": "signal_id",
  "value": 0.0,
  "threshold": "condition description",
  "timestamp": "ISO-8601"
}}
```

---

## 4. Architecture Diagram

```mermaid
graph TD
    REQ["Requirement Input"] --> PARSER["GenAI Requirement Parser"]
    PARSER --> BLUEPRINT["Blueprint JSON"]
    BLUEPRINT --> CODEGEN["Code Generator"]
    BLUEPRINT --> DESIGNGEN["Design Generator"]
    BLUEPRINT --> TESTGEN["Test Generator"]
    CODEGEN --> PY["Python Service"]
    CODEGEN --> CPP["C++ Service (MISRA)"]
    CODEGEN --> KT["Kotlin Service"]
    CODEGEN --> RS["Rust Service"]
    PY --> API["REST API Layer"]
    API --> SIM["Simulator"]
    API --> ANA["Analytics Engine"]
    API --> HMI["HMI Dashboard"]
```

## 5. Component Diagram

```mermaid
classDiagram
    class VehicleTelemetry {{
{signal_attrs}
        +string timestamp
        +string engine_status
    }}

    class VehicleService {{
        +get_all_telemetry() VehicleTelemetry
{service_methods}
        +get_alerts(limit) List~Alert~
    }}

    class HealthAnalyzer {{
        +analyze(telemetry) List~Alert~
    }}

    class Simulator {{
        +start() SimulationStatus
        +stop() SimulationStatus
        +generate_telemetry() VehicleTelemetry
    }}

    VehicleService --> VehicleTelemetry
    VehicleService --> HealthAnalyzer
    Simulator --> VehicleTelemetry
{ui_boxes}
```

## 6. Data Flow

1. **Requirement Input** → User provides natural-language requirement
2. **GenAI Parser** → Extracts signals, services, UI components, alerts into blueprint
3. **Code Generator** → Generates source code in Python, C++, Kotlin, Rust
4. **Design Generator** → Produces this design document
5. **Test Generator** → Creates test cases for validation
6. **Service Deployment** → Generated service is deployed/compiled
7. **Simulation** → Simulator generates realistic telemetry data
8. **Analytics** → Health analyzer detects anomalies and generates alerts
9. **HMI** → Dashboard visualizes data in real-time

## 7. Traceability Matrix

| Requirement | Signal | API Endpoint | UI Component | Alert |
|-------------|--------|-------------|--------------|-------|
"""
    for sig in signals:
        endpoint = sig.replace("_", "-")
        widget = next((u for u in ui_components if sig.split("_")[0] in u), "Auto-generated")
        sig_alerts = [a for a in alerts if sig.split("_")[0] in a]
        alert_str = ", ".join(sig_alerts) if sig_alerts else "—"
        doc += f"| {req[:40]}... | `{sig}` | `/vehicle/{endpoint}` | `{widget}` | {alert_str} |\n"

    return doc


# ── LLM-based design generation ─────────────────────────────────────────────

_DESIGN_PROMPT = """You are an expert automotive software architect. Generate a detailed Service Interface Design Document in Markdown format.

REQUIREMENT: "{requirement}"

BLUEPRINT:
- Signals: {signals}
- Services: {services}
- UI Components: {ui_components}
- Alerts: {alerts}

The document MUST include:
1. Requirement summary
2. API contract table (Method, Endpoint, Description, Response)
3. Data model definitions (JSON schema)
4. Mermaid architecture diagram
5. Mermaid class diagram
6. Data flow description
7. Traceability matrix (Requirement → Signal → API → UI → Alert)

Generate the complete Markdown document."""


# ── Public API ───────────────────────────────────────────────────────────────

def generate_design(
    blueprint: Dict[str, Any],
    use_llm: bool = True,
    provider_name: Optional[str] = None,
) -> DesignDocument:
    """
    Generate a design document from a requirement blueprint.
    """
    start = time.perf_counter()
    method = "template"
    llm_metrics = None

    if use_llm:
        provider = get_provider(provider_name)
        if provider.name != "template":
            try:
                prompt = _DESIGN_PROMPT.format(
                    requirement=blueprint.get("raw_requirement", ""),
                    signals=", ".join(blueprint.get("signals", [])),
                    services=", ".join(blueprint.get("services", [])),
                    ui_components=", ".join(blueprint.get("ui_components", [])),
                    alerts=", ".join(blueprint.get("alerts", [])),
                )
                response = provider.generate(prompt)
                record_metrics(response.metrics)
                elapsed = (time.perf_counter() - start) * 1000

                return DesignDocument(
                    title="Service Interface Design Document",
                    content=response.text,
                    format="markdown",
                    generation_method=f"llm:{provider.name}",
                    generation_time_ms=round(elapsed, 1),
                    llm_metrics=response.metrics,
                )
            except Exception as exc:
                logger.warning(f"LLM design generation failed, using template: {exc}")

    # Template fallback
    content = _generate_design_from_template(blueprint)
    elapsed = (time.perf_counter() - start) * 1000

    return DesignDocument(
        title="Service Interface Design Document",
        content=content,
        format="markdown",
        generation_method=method,
        generation_time_ms=round(elapsed, 1),
    )
