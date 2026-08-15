import os
import json
import time
os.environ["ROS_DOMAIN_ID"] = "0"
os.environ.pop("ROS_AUTOMATIC_DISCOVERY_RANGE", None)
os.environ["RMW_IMPLEMENTATION"] = "rmw_fastrtps_cpp"
os.environ["ROS_SUPER_CLIENT"] = "True"
os.environ["ROS_DISCOVERY_SERVER"] = "192.168.0.129:11811;"

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.experiment_audit import emit_event

from backend.api.settings_routes import router as settings_router
from backend.api.health_routes import router as health_router
from backend.api.cobot_routes import router as cobot_router
from backend.api.cell_routes import router as cell_router
from backend.api.turtlebot_routes import router as turtlebot_router

app = FastAPI(
    title="Future Lab Control Center API",
    description="API de Gerenciamento e Controle Unificado da Célula (MyCobot 280 + TurtleBot 4)",
    version="1.0.0",
)

# Permite conexões do frontend web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def audit_mutating_dashboard_commands(request: Request, call_next):
    """Registra comandos HTTP; leituras periódicas do dashboard não geram ruído."""
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return await call_next(request)
    started = time.monotonic()
    raw_body = await request.body()
    body = None
    if raw_body:
        try:
            body = json.loads(raw_body[:65536])
        except Exception:
            body = raw_body[:2048].decode("utf-8", errors="replace")
    base = {
        "method": request.method,
        "path": request.url.path,
        "query": str(request.url.query),
        "body": body,
        "client": request.client.host if request.client else None,
    }
    try:
        response = await call_next(request)
        emit_event("dashboard_command", {
            **base,
            "status_code": response.status_code,
            "duration_ms": round((time.monotonic() - started) * 1000.0, 3),
        })
        return response
    except Exception as exc:
        emit_event("dashboard_command", {
            **base,
            "status_code": 500,
            "duration_ms": round((time.monotonic() - started) * 1000.0, 3),
            "exception": repr(exc),
        })
        raise

# Registra os roteadores de API
app.include_router(settings_router)
app.include_router(health_router)
app.include_router(cobot_router)
app.include_router(cell_router)
app.include_router(turtlebot_router)

@app.on_event("startup")
def startup_event():
    """Garante que nenhum processo de teste do YOLO inicie sozinho ao abrir a aplicação."""
    try:
        from backend.api.cobot_routes import stop_yolo_test_process
        stop_yolo_test_process()
    except Exception as e:
        print(f"[WARN] Erro ao limpar processo YOLO no startup: {e}")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "Future Lab Control Center API",
        "version": "1.0.0",
        "endpoints": [
            "/api/v1/health",
            "/api/v1/settings",
            "/api/v1/cobot/poses",
            "/api/v1/cell/status",
            "/api/v1/turtlebot/status"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    from backend.config.settings import get_settings
    settings = get_settings()
    # Este processo mantem um no rclpy e threads de executor persistentes.
    # O reloader de desenvolvimento cria processos filhos e pode deixar
    # participantes/endpoints DDS antigos visiveis durante as substituicoes.
    uvicorn.run(app, host="0.0.0.0", port=settings.BACKEND_PORT, reload=False)
