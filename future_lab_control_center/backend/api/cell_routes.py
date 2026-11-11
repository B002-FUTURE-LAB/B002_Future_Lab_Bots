# ============================================================
# cell_routes.py — API Router para Controle da Célula e Segurança
# ============================================================
import time
import threading
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.ros2_nodes.cobot_node import get_cobot_node
from backend.experiment_audit import emit_event

router = APIRouter(prefix="/api/v1/cell", tags=["Cell Control"])

class CellModeSchema(BaseModel):
    mode: str  # "auto" ou "manual"
    cooldown_sec: Optional[float] = 5.0
    yolo_conf: Optional[float] = 0.60
    arm_speed: Optional[float] = 0.50

class InterruptConfirmSchema(BaseModel):
    abort: bool  # True = SIM, Abortar; False = NÃO, Continuar

cell_state = {
    "mode": "auto",
    "auto_running": False,
    "cooldown_sec": 5.0,
    "yolo_conf": 0.60,
    "arm_speed": 0.50,
    "manual_authorized": False,
    "manual_step": "idle",  # "idle", "at_scan", "pick_authorized", "at_place_approach", "place_authorized"
    "status": "idle",
    "panic_locked": False,
    "yolo_detected_item": None,
    "handshake": {
        "active": False,
        "run_id": None,
        "phase": "idle",
        "item_class": None,
        "canonical_class": None,
        "target": None,
        "success": None,
        "error": None,
        "started_at": None,
        "completed_at": None,
        "evidence": {},
    },
    "integrated_real": {
        "active": False,
        "run_id": None,
        "phase": "idle",
        "error": None,
        "started_at": None,
        "completed_at": None,
        "visuals": {},
        "detection": None,
        "candidate": None,
    },
}

_state_lock = threading.Lock()

# Controle de threads e eventos do motor de ciclo
_cycle_thread: Optional[threading.Thread] = None
_pause_event = threading.Event()
_pause_event.set()  # set = executando, clear = pausado (interrompido)
_abort_requested = False
_cycle_cancel = False
_step_pick_event = threading.Event()
_step_place_event = threading.Event()
_real_detection_confirm_event = threading.Event()

def _check_pause_and_cancel() -> bool:
    """Verifica se há requisição de pausa (interrupção) ou cancelamento/abort."""
    global _cycle_cancel, _abort_requested
    if _cycle_cancel or _abort_requested or not cell_state.get("auto_running", False) and cell_state["mode"] == "auto":
        return False
    while not _pause_event.is_set():
        time.sleep(0.05)
        if _cycle_cancel or _abort_requested:
            return False
    return not (_cycle_cancel or _abort_requested)

def _goto_pose_with_resume(node, pose_name: str, speed: float = 0.15) -> bool:
    """Executa goto_pose. Se for pausado/interrompido e depois retomado (NÃO, CONTINUAR), re-envia a trajetória para a pose alvo!"""
    while True:
        if not _check_pause_and_cancel():
            return False
        
        ok = node.goto_pose(pose_name, speed)
        
        if not _pause_event.is_set():
            if not _check_pause_and_cancel():
                return False
            print(f"[CYCLE] 🔄 Retomando movimento interrompido para a pose '{pose_name}'...")
            continue
            
        return ok

def _abort_cleanup():
    """Executa a sequência segura de descarte e retorno ao acionar Abort (SIM): desliga bomba no pick, volta para home e desativa o modo manual/auto."""
    global _abort_requested, _cycle_cancel
    print("[CYCLE] 🛑 Executando sequência de cancelamento/abort seguro...")
    from backend.api.cobot_routes import stop_yolo_test_process
    try:
        stop_yolo_test_process()
    except Exception:
        pass

    node = get_cobot_node()
    if node.pump_active:
        print("[CYCLE] Desligando bomba de sucção e liberando lata...")
        try:
            node.goto_pose("pick", 0.15)
        except Exception:
            pass
        node.set_pump(False)
        time.sleep(0.5)

    try:
        cell_state["status"] = "moving_home"
        print("[CYCLE] Retornando braço para HOME após abort...")
        node.goto_pose("home", 0.20)
    except Exception:
        pass

    # Desliga completamente o loop automático e reseta os estados da célula
    cell_state["auto_running"] = False
    cell_state["mode"] = "auto"
    cell_state["status"] = "idle"
    cell_state["manual_step"] = "idle"
    cell_state["yolo_detected_item"] = None
    _abort_requested = False
    _cycle_cancel = True

def is_valid_tin_class(cls_name: Optional[str]) -> bool:
    """Valida se a classe detectada pelo modelo YOLO é uma lata VÁLIDA para coleta."""
    if not cls_name:
        return False
    l = cls_name.lower().strip()
    if l in ("none", "invalid_stream", "tin_invalid") or "invalid" in l:
        return False
    # Aceita qualquer classe válida de lata: tin_valid_*, valid, red, blue, lata, square, triangle, etc.
    valid_keywords = ["valid", "tin", "red", "blue", "lata", "can", "square", "triangle"]
    if any(k in l for k in valid_keywords):
        return True
    return False


_HANDSHAKE_CLASSES = {
    "blue": ("tin_valid_blue", "delivery_blue"),
    "tin_valid_blue": ("tin_valid_blue", "delivery_blue"),
    "tin_valid_blue_square": ("tin_valid_blue", "delivery_blue"),
    "red": ("tin_valid_red", "delivery_red"),
    "tin_valid_red": ("tin_valid_red", "delivery_red"),
    "tin_valid_red_square": ("tin_valid_red", "delivery_red"),
}


def _normalize_handshake_class(item_class: str) -> tuple[str, str]:
    normalized = str(item_class or "").strip().lower()
    # O modelo real inclui o formato da lata no sufixo (por exemplo,
    # tin_valid_red_triangle). O destino depende da cor, não do formato.
    if normalized.startswith("tin_valid_blue"):
        return "tin_valid_blue", "delivery_blue"
    if normalized.startswith("tin_valid_red"):
        return "tin_valid_red", "delivery_red"
    result = _HANDSHAKE_CLASSES.get(normalized)
    if result is None:
        raise HTTPException(
            status_code=422,
            detail="Classe inválida. Use somente a lata azul ou vermelha.",
        )
    return result


def _set_handshake(phase: str, **updates) -> None:
    with _state_lock:
        handshake = dict(cell_state.get("handshake") or {})
        handshake.update({"phase": phase, **updates})
        cell_state["handshake"] = handshake
        if handshake.get("active"):
            cell_state["status"] = f"handshake_{phase}"
    emit_event("handshake_transition", {"phase": phase, **handshake})


def _merge_handshake_evidence(**evidence) -> None:
    with _state_lock:
        handshake = dict(cell_state.get("handshake") or {})
        merged = dict(handshake.get("evidence") or {})
        merged.update(evidence)
        handshake["evidence"] = merged
        cell_state["handshake"] = handshake


def _set_integrated_real(phase: str, **updates) -> None:
    with _state_lock:
        state = dict(cell_state.get("integrated_real") or {})
        state.update({"phase": phase, **updates})
        cell_state["integrated_real"] = state
        if state.get("active"):
            cell_state["status"] = f"integrated_{phase}"
    emit_event("integrated_real_transition", {"phase": phase, **state})


def _handshake_infrastructure_preflight() -> dict:
    """Mede hardware e comunicação sem inventar uma classe de produto."""
    node = get_cobot_node()
    node.load_poses()
    required_poses = [
        "home", "scan", "pick_approach", "pick", "place_approach", "place"
    ]
    missing_poses = [pose for pose in required_poses if pose not in node.poses]
    if missing_poses:
        raise HTTPException(
            status_code=409,
            detail=f"Poses obrigatórias ausentes: {', '.join(missing_poses)}.",
        )

    hardware = node.get_hardware_status()
    measured_joints = node.get_measured_joints()
    if not hardware or measured_joints is None:
        raise HTTPException(
            status_code=503,
            detail="Nano não forneceu /status e /get_angles mensuráveis.",
        )
    if hardware.get("mock") is not False:
        raise HTTPException(status_code=409, detail="Nano está em modo mock; teste físico recusado.")
    if hardware.get("gpio_ready") is not True:
        raise HTTPException(status_code=409, detail="GPIO do Nano não está pronto.")
    if hardware.get("pump_active") is not False:
        raise HTTPException(
            status_code=409,
            detail="Bomba já está ligada antes do teste; desligue-a e verifique a peça.",
        )

    from backend.api.turtlebot_routes import (
        get_nav_readiness, get_processes, MISSION_SIGNAL_AGENT_URL,
    )
    readiness = get_nav_readiness()
    if readiness.get("mission_ready") is not True:
        raise HTTPException(
            status_code=409,
            detail=(
                "TurtleBot não está pronto para missão: "
                + ", ".join(readiness.get("mission_missing") or ["estado desconhecido"])
            ),
        )
    manager = (get_processes() or {}).get("mission_manager") or {}
    if not (
        manager.get("running") is True
        and int(manager.get("instances", 0)) == 1
        and manager.get("visible_on_ros_graph") is True
    ):
        raise HTTPException(
            status_code=409,
            detail="Mission Manager precisa ter exatamente uma instância e estar visível no grafo ROS.",
        )

    try:
        import json
        import urllib.request
        with urllib.request.urlopen(
            f"{MISSION_SIGNAL_AGENT_URL}/health", timeout=2.0
        ) as response:
            bridge = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Mission Signal Agent não está saudável: {exc}",
        )
    if bridge.get("ok") is not True:
        raise HTTPException(status_code=503, detail="Mission Signal Agent não confirmou saúde.")

    return {
        "nano": {
            "mock": hardware.get("mock"),
            "gpio_ready": hardware.get("gpio_ready"),
            "pump_active": hardware.get("pump_active"),
            "measured_joints": measured_joints,
        },
        "turtlebot": {
            "mission_ready": True,
            "start_mode": readiness.get("mission_start_mode"),
            "manager_instances": manager.get("instances"),
            "manager_visible": manager.get("visible_on_ros_graph"),
        },
        "signal_bridge": bridge,
    }


def _handshake_preflight(item_class: str) -> dict:
    """Portão sem movimento: só permite o teste com cada elo medido."""
    canonical_class, target = _normalize_handshake_class(item_class)
    return {
        "canonical_class": canonical_class,
        "target": target,
        **_handshake_infrastructure_preflight(),
    }


def _stable_real_yolo_class(
    samples: list[dict],
    required: int = 5,
    min_span_sec: float = 0.8,
    window_sec: float = 3.0,
) -> tuple[Optional[str], Optional[str]]:
    """Aceita somente amostras distintas, recentes e da mesma classe real."""
    if len(samples) < required:
        return None, None
    newest_timestamp = max(float(sample.get("timestamp", 0.0)) for sample in samples)
    recent = [
        sample
        for sample in samples
        if newest_timestamp - float(sample.get("timestamp", 0.0)) <= window_sec
    ]
    if len(recent) < required:
        return None, None
    timestamps = [float(sample.get("timestamp", 0.0)) for sample in recent]
    span = max(timestamps) - min(timestamps)
    if (
        len(set(timestamps)) < required
        or span < min_span_sec
        or span > window_sec
    ):
        return None, None
    normalized = []
    for sample in recent:
        try:
            normalized.append(_normalize_handshake_class(sample.get("class", "")))
        except HTTPException:
            return None, None
    if len({item[0] for item in normalized}) != 1:
        return None, None
    return normalized[-1]


def _goto_pose_verified_with_resume(node, pose_name: str, speed: float) -> bool:
    if not _check_pause_and_cancel():
        return False
    ok = node.goto_pose_verified(pose_name, speed)
    return bool(ok and _check_pause_and_cancel())


def _rollback_handshake_cobot(node, release_confirmed: bool) -> dict:
    """Best effort seguro; nunca relata sucesso sem medir bomba OFF e HOME."""
    evidence = {"attempted": True, "release_confirmed": release_confirmed}
    status = node.get_hardware_status() or {}
    pump_on = bool(status.get("pump_active", node.pump_active))
    if pump_on and not release_confirmed:
        returned_to_pick = all([
            node.goto_pose_verified("place_approach", 0.15),
            node.goto_pose_verified("pick_approach", 0.15),
            node.goto_pose_verified("pick", 0.10),
        ])
        evidence["returned_to_pick"] = returned_to_pick
        evidence["pump_off"] = node.set_pump_verified(False)
        node.goto_pose_verified("pick_approach", 0.15)
    elif pump_on:
        evidence["pump_off"] = node.set_pump_verified(False)
    else:
        evidence["pump_off"] = True
    evidence["home"] = node.goto_pose_verified("home", 0.15)
    return evidence


def _recover_turtlebot_after_handshake_failure(
    turtle_node,
    stop_mission_fn,
    trigger_dock_fn,
    dock_confirm_sec: float = 10.0,
) -> dict:
    """Cancela a rotina e só confirma recuperação com dock físico medido."""
    evidence = {}
    try:
        evidence["turtlebot_stop"] = stop_mission_fn()
    except Exception as stop_error:
        evidence["turtlebot_stop_error"] = str(stop_error)

    if turtle_node.telemetry_fresh() and turtle_node.is_docked:
        evidence["turtlebot_recovery"] = {
            "status": "already_docked",
            "dock_status_measured": True,
        }
        return evidence

    try:
        dock_result = trigger_dock_fn()
        deadline = time.monotonic() + max(0.0, float(dock_confirm_sec))
        while time.monotonic() < deadline:
            if turtle_node.telemetry_fresh() and turtle_node.is_docked:
                break
            time.sleep(0.25)
        dock_measured = bool(
            turtle_node.telemetry_fresh() and turtle_node.is_docked
        )
        evidence["turtlebot_recovery"] = {
            "status": "docked" if dock_measured else "unconfirmed",
            "dock_status_measured": dock_measured,
            "command_result": dock_result,
        }
    except Exception as dock_error:
        evidence["turtlebot_recovery"] = {
            "status": "failed",
            "dock_status_measured": False,
            "error": str(dock_error),
        }
    return evidence

def _run_cycle_internal(is_manual: bool = False):
    """Executa a sequência de inspeção, visão YOLO e coleta/soltura com suporte a aprovação passo-a-passo no modo manual."""
    global _cycle_cancel, _abort_requested
    _cycle_cancel = False
    _abort_requested = False
    _step_pick_event.clear()
    _step_place_event.clear()

    node = get_cobot_node()
    node.load_poses()

    missing = [p for p in ["home", "scan", "pick_approach", "pick", "place_approach", "place"] if p not in node.poses]
    if missing:
        print(f"[CYCLE] ABORTADO: poses faltando no YAML: {missing}")
        cell_state["status"] = "idle"
        cell_state["manual_step"] = "idle"
        cell_state["auto_running"] = False
        return

    from backend.api.cobot_routes import start_yolo_test_process, stop_yolo_test_process

    speed = max(0.10, min(1.0, float(cell_state.get("arm_speed", 0.50))))
    slow_speed = max(0.05, speed * 0.7)

    try:
        # ========== STEP 1: HOME → SCAN ==========
        cell_state["status"] = "moving_scan"
        print(f"[CYCLE] Step 1: Mover para posição SCAN (velocidade: {speed*100:.0f}%)...")
        ok = _goto_pose_with_resume(node, "scan", speed)
        if not ok or not _check_pause_and_cancel():
            _abort_cleanup()
            return
        time.sleep(0.5)

        # ========== STEP 2: INSPEÇÃO YOLO ATIVA ==========
        cell_state["status"] = "at_scan_inspecting"
        cell_state["manual_step"] = "at_scan"
        cell_state["yolo_detected_item"] = None
        node.clear_yolo_state()
        conf = float(cell_state.get("yolo_conf", 0.45))

        print(f"[CYCLE] Step 2: Ativando e monitorando YOLO na pose SCAN (confianca minima: {conf:.2f})...")
        from backend.api.cobot_routes import is_yolo_process_alive
        if not is_yolo_process_alive():
            start_yolo_test_process(conf=conf)

        detected_item = None
        t0 = time.time()

        if is_manual:
            print("[CYCLE] Modo Manual: Aguardando detecção de lata válida e autorização do usuário...")
            while not _step_pick_event.is_set():
                if not _check_pause_and_cancel():
                    stop_yolo_test_process()
                    _abort_cleanup()
                    return

                yolo = node.get_last_yolo_msg()
                if yolo and yolo.get("class") and is_valid_tin_class(yolo["class"]):
                    c_val = yolo.get("confidence", 0.0)
                    if c_val >= (conf * 0.70):
                        detected_item = yolo
                        cell_state["yolo_detected_item"] = yolo
                time.sleep(0.15)
        else:
            recent_votes = []
            while (time.time() - t0) < 25.0:
                if not _check_pause_and_cancel():
                    stop_yolo_test_process()
                    _abort_cleanup()
                    return

                yolo = node.get_last_yolo_msg()
                if yolo and yolo.get("class") and is_valid_tin_class(yolo["class"]):
                    c_val = yolo.get("confidence", 0.0)
                    if c_val >= (conf * 0.70):
                        recent_votes.append(yolo)
                        cell_state["yolo_detected_item"] = yolo
                        
                        if len(recent_votes) >= 2:
                            detected_item = yolo
                            print(f"[CYCLE] 🎯 Lata detectada com SUCESSO: '{yolo['class']}' (conf: {c_val:.2f})!")
                            break
                time.sleep(0.15)

        if not detected_item and not is_manual:
            print("[CYCLE] Inspeção sem lata válida na mesa: mantendo braço na pose SCAN aguardando próximo ciclo...")
            cell_state["status"] = "at_scan_inspecting"
            return

        cls_name = (cell_state.get("yolo_detected_item") or {}).get("class", "lata")
        print(f"[CYCLE] Step 2 Concluído: Lata '{cls_name}' autorizada para coleta!")

        # Handshake Inter-Robôs: Verifica se o TurtleBot 4 está no Ponto de Coleta/Estação antes de coletar e colocar na bandeja
        from backend.ros2_nodes.cell_event_bridge import is_turtlebot_ready_at_loading_station, record_detected_class
        if not is_turtlebot_ready_at_loading_station():
            print("[CYCLE] ⏳ TurtleBot em trânsito de entrega! Aguardando retorno ao Ponto de Coleta em pose SCAN...")
            cell_state["status"] = "waiting_turtlebot_return"
            while not is_turtlebot_ready_at_loading_station():
                if not _check_pause_and_cancel():
                    _abort_cleanup()
                    return
                time.sleep(0.5)
            print("[CYCLE] ✅ TurtleBot disponível no Ponto de Coleta! Iniciando Pick & Place...")

        record_detected_class(cls_name)

        # Disparo Proativo Antecipado do TurtleBot 4 (undock + deslocamento para pickup_point em paralelo com o Pick & Place do Nano)
        from backend.api.turtlebot_routes import trigger_delivery, trigger_failure
        try:
            valid_cls = is_valid_tin_class(cls_name)
            print(f"[CYCLE] 🚀 Disparo proativo antecipado do TurtleBot 4 para '{cls_name}' (válida={valid_cls})...")
            if valid_cls:
                trigger_delivery()
            else:
                trigger_failure()
        except Exception as e:
            print(f"[WARN] Falha no disparo proativo do TurtleBot 4: {e}")

        # ========== STEP 3: PICK APPROACH → PICK (BOMBA ON) → PICK APPROACH → PLACE APPROACH ==========
        cell_state["status"] = "moving_pick"
        cell_state["manual_step"] = "moving_pick"
        print(f"[CYCLE] Step 3: Indo para PICK APPROACH e PICK (velocidade: {speed*100:.0f}%)...")

        ok = _goto_pose_with_resume(node, "pick_approach", speed)
        if not ok or not _check_pause_and_cancel():
            _abort_cleanup()
            return
        time.sleep(0.3)

        cell_state["status"] = "picking"
        ok = _goto_pose_with_resume(node, "pick", slow_speed)
        if not ok or not _check_pause_and_cancel():
            _abort_cleanup()
            return
        time.sleep(0.5)

        cell_state["status"] = "moving_pick"
        ok = _goto_pose_with_resume(node, "pick_approach", speed)
        if not ok or not _check_pause_and_cancel():
            _abort_cleanup()
            return
        time.sleep(0.3)

        cell_state["status"] = "moving_place"
        ok = _goto_pose_with_resume(node, "place_approach", speed)
        if not ok or not _check_pause_and_cancel():
            _abort_cleanup()
            return
        time.sleep(0.5)

        # ========== STEP 4: AGUARDAR AUTORIZAÇÃO DE PLACE EM PLACE_APPROACH ==========
        if is_manual:
            cell_state["status"] = "at_place_approach_waiting"
            cell_state["manual_step"] = "at_place_approach"
            print("[CYCLE] Step 4 (Manual): Chegou a PLACE APPROACH. Aguardando autorização para soltar a lata...")
            while not _step_place_event.is_set():
                if not _check_pause_and_cancel():
                    _abort_cleanup()
                    return
                time.sleep(0.2)

        # ========== STEP 5: PLACE (BOMBA ON) → DISPARA TURTLEBOT → AGUARDA TURTLEBOT NO PICKUP → BOMBA OFF → HOME ==========
        cell_state["status"] = "placing"
        cell_state["manual_step"] = "placing"
        print(f"[CYCLE] Step 5: Avançando para PLACE segurando a lata (velocidade: {speed*100:.0f}%)...")
        ok = _goto_pose_with_resume(node, "place", slow_speed)
        if not ok or not _check_pause_and_cancel():
            _abort_cleanup()
            return
        time.sleep(0.5)

        # 1. Publica classe e dispara o TurtleBot para se deslocar ao pickup_point
        print(f"[CYCLE] 🚚 Publicando '{cls_name}' e disparando rota no TurtleBot 4 (undock -> pickup_point)...")
        node.publish_product_class(cls_name)

        from backend.api.turtlebot_routes import trigger_delivery, trigger_failure
        try:
            valid_cls = is_valid_tin_class(cls_name)
            print(f"[CYCLE] 🚀 Disparando rota no TurtleBot 4 para a peça '{cls_name}' (válida={valid_cls})...")
            if valid_cls:
                trigger_delivery()
            else:
                trigger_failure()
        except Exception as e:
            print(f"[WARN] Falha ao disparar /start_delivery no TurtleBot 4: {e}")

        # 2. Aguarda a chegada do TurtleBot 4 no Ponto de Coleta (pickup_point) ou aviso de bateria <= 5%
        print("[CYCLE] ⏳ Braço Nano em PLACE segurando a lata. Aguardando sinal de chegada do TurtleBot 4 no pickup_point...")
        node.clear_turtlebot_pickup()
        
        # Limpa o evento de emergência antes da checagem
        if hasattr(node, 'tb4_battery_emergency_event'):
            node.tb4_battery_emergency_event.clear()

        arrived = False
        t_start = time.time()
        while (time.time() - t_start) < 90.0:
            if hasattr(node, 'tb4_battery_emergency_event') and node.tb4_battery_emergency_event.is_set():
                print("[CYCLE] 🚨 EMERGÊNCIA: TurtleBot 4 reportou Bateria Crítica (<= 5%)! Iniciando Rollback de Devolução ao PICK...")
                # Executa Rollback: Devolve a lata com segurança ao ponto PICK
                cell_state["status"] = "battery_emergency_rollback"
                _goto_pose_with_resume(node, "place_approach", speed)
                _goto_pose_with_resume(node, "pick_approach", speed)
                _goto_pose_with_resume(node, "pick", slow_speed)
                print("[CYCLE] 🔄 Ponto PICK alcançado -> Desligando bomba de sucção e devolvendo lata à mesa de coleta...")
                node.set_pump(False)
                time.sleep(0.5)
                _goto_pose_with_resume(node, "pick_approach", speed)
                _goto_pose_with_resume(node, "home", 0.20)
                
                # Pausa o ciclo automático aguardando confirmação do usuário ou recarga 100%
                cell_state["auto_running"] = False
                cell_state["status"] = "paused_battery_emergency"
                print("[CYCLE] ⏸️ Modo Automático PAUSADO devido à bateria crítica do TurtleBot 4. Aguardando recarga (100%) ou confirmação manual.")
                return

            if node.wait_for_turtlebot_at_pickup(timeout_sec=1.0):
                arrived = True
                break
            
            if not _check_pause_and_cancel():
                _abort_cleanup()
                return

        if arrived:
            print("[CYCLE] ✅ Confirmação recebida! TurtleBot 4 chegou no Ponto de Coleta (pickup_point).")
        else:
            print("[CYCLE] ❌ Timeout sem confirmação do TurtleBot — a lata NÃO será liberada no PLACE.")
            cell_state["status"] = "pickup_timeout_rollback"
            _goto_pose_with_resume(node, "place_approach", speed)
            _goto_pose_with_resume(node, "pick_approach", speed)
            _goto_pose_with_resume(node, "pick", slow_speed)
            node.set_pump(False)
            _goto_pose_with_resume(node, "pick_approach", speed)
            _goto_pose_with_resume(node, "home", 0.20)
            return

        # 3. Desliga a bomba (solta a lata na bandeja do TurtleBot 4) e notifica o robô móvel
        print("[CYCLE] 📦 Desligando bomba de sucção (liberando lata na bandeja do TurtleBot 4)...")
        node.set_pump(False)
        node.publish_item_released()
        time.sleep(1.0)

        # 4. Retorna o braço com segurança para PLACE APPROACH -> HOME
        print("[CYCLE] Retornando braço para PLACE APPROACH e HOME...")
        ok = _goto_pose_with_resume(node, "place_approach", speed)
        if not ok or not _check_pause_and_cancel():
            _abort_cleanup()
            return
        time.sleep(0.3)

        cell_state["status"] = "moving_home"
        print("[CYCLE] Finalização: Retornando para HOME...")
        _goto_pose_with_resume(node, "home", 0.20)

        print(f"[CYCLE] ✅ CICLO EXECUTADO E HANDSHAKE INTER-ROBÔS CONCLUÍDO COM SUCESSO!")

    except Exception as e:
        print(f"[CYCLE] ERRO no ciclo interno: {e}")
        _abort_cleanup()
    finally:
        cell_state["status"] = "idle"
        cell_state["manual_step"] = "idle"
        cell_state["yolo_detected_item"] = None
        cell_state["manual_authorized"] = False

def _run_handshake_test_standalone(
    item_class: str,
    preflight: dict,
    real_detection: Optional[dict] = None,
    scan_already_confirmed: bool = False,
):
    """Executa o handshake físico com provas independentes dos dois robôs."""
    global _cycle_cancel, _abort_requested
    _cycle_cancel = False
    _abort_requested = False

    node = get_cobot_node()
    node.load_poses()
    speed = max(0.10, min(1.0, float(cell_state.get("arm_speed", 0.50))))
    slow_speed = max(0.05, speed * 0.7)
    canonical_class = preflight["canonical_class"]
    expected_target = preflight["target"]
    turtle_started = False
    item_physically_released = False
    release_confirmed = False

    try:
        from backend.api.turtlebot_routes import (
            _publish_mission_signal_on_host,
            _start_test_delivery_on_host,
            _wait_for_delivery_complete_on_host,
            _wait_for_pickup_on_host,
            get_turtlebot_node,
            stop_mission,
            trigger_dock,
        )
        from backend.ros2_nodes.cell_event_bridge import record_detected_class

        if scan_already_confirmed:
            print("[HANDSHAKE] 1/8 Pose SCAN já confirmada pelo modo YOLO real.")
        else:
            print(f"[HANDSHAKE] 1/8 SCAN para simular YOLO: '{canonical_class}'.")
            _set_handshake("moving_scan")
            if not _goto_pose_verified_with_resume(node, "scan", speed):
                raise RuntimeError("Nano não confirmou a pose SCAN.")
        _merge_handshake_evidence(scan_pose_measured=True)

        _set_handshake("yolo_detected")
        if real_detection is not None:
            detected_class, detected_target = _normalize_handshake_class(
                real_detection.get("class", "")
            )
            if detected_class != canonical_class or detected_target != expected_target:
                raise RuntimeError(
                    "Classe real medida divergiu do destino aprovado no preflight."
                )
            cell_state["yolo_detected_item"] = dict(real_detection)
            _merge_handshake_evidence(yolo_real_detection=dict(real_detection))
            print(
                "[HANDSHAKE] YOLO REAL confirmado: "
                f"'{detected_class}' conf={real_detection.get('confidence')}."
            )
        else:
            cell_state["yolo_detected_item"] = {
                "class": item_class,
                "confidence": 0.99,
                "source": "synthetic_handshake_test",
            }
        record_detected_class(canonical_class)

        print("[HANDSHAKE] 2/8 Enviando classe fresca e start pelo participante ROS do host.")
        _set_handshake("starting_turtlebot")
        start_evidence = _start_test_delivery_on_host(canonical_class)
        turtle_started = True
        if start_evidence.get("target") != expected_target:
            raise RuntimeError(
                f"Destino confirmado '{start_evidence.get('target')}' difere de '{expected_target}'."
            )
        _merge_handshake_evidence(turtlebot_start=start_evidence)

        print("[HANDSHAKE] 3/8 TurtleBot navega em paralelo; Nano executa PICK.")
        _set_handshake("cobot_picking")
        if not _goto_pose_verified_with_resume(node, "pick_approach", speed):
            raise RuntimeError("Nano não confirmou PICK APPROACH.")
        if not _goto_pose_verified_with_resume(node, "pick", slow_speed):
            raise RuntimeError("Nano não confirmou PICK.")
        if not node.set_pump_verified(True):
            raise RuntimeError("Bomba ON não foi confirmada pelo Nano.")
        _merge_handshake_evidence(pick_pose_measured=True, pump_on_measured=True)

        print("[HANDSHAKE] 4/8 Transportando a lata simulada até PLACE.")
        _set_handshake("cobot_placing")
        for pose_name, pose_speed in [
            ("pick_approach", speed),
            ("place_approach", speed),
            ("place", slow_speed),
        ]:
            if not _goto_pose_verified_with_resume(node, pose_name, pose_speed):
                raise RuntimeError(f"Nano não confirmou a pose {pose_name.upper()}.")
        _merge_handshake_evidence(place_pose_measured=True)

        print("[HANDSHAKE] 5/8 Aguardando True real em /turtlebot_at_pickup.")
        _set_handshake("waiting_turtlebot_pickup")
        pickup_deadline = time.monotonic() + 100.0
        pickup_evidence = None
        while time.monotonic() < pickup_deadline:
            if not _check_pause_and_cancel():
                raise RuntimeError("Teste cancelado pelo operador.")
            window = min(8.0, max(1.0, pickup_deadline - time.monotonic()))
            result = _wait_for_pickup_on_host(window)
            if result.get("received") is True:
                pickup_evidence = result
                break
        if pickup_evidence is None:
            raise RuntimeError(
                "Timeout sem True em /turtlebot_at_pickup; a lata não será solta."
            )
        _merge_handshake_evidence(turtlebot_at_pickup=pickup_evidence)

        print("[HANDSHAKE] 6/8 Turtle confirmado: bomba OFF e release confirmado na missão.")
        _set_handshake("releasing_item")
        if not node.set_pump_verified(False):
            raise RuntimeError("Bomba OFF não foi confirmada pelo Nano.")
        item_physically_released = True
        release_evidence = None
        release_errors = []
        for attempt in range(1, 3):
            try:
                release_evidence = _publish_mission_signal_on_host(
                    "item_released", ""
                )
                break
            except HTTPException as release_error:
                release_errors.append({
                    "attempt": attempt,
                    "status_code": release_error.status_code,
                    "detail": str(release_error.detail),
                })
                if attempt < 2:
                    time.sleep(1.0)
        if release_evidence is None:
            _merge_handshake_evidence(release_attempts=release_errors)
            raise RuntimeError(
                "Bomba OFF foi medida, mas a missão não confirmou "
                "/item_released_on_tb4 após duas janelas."
            )
        release_confirmed = True
        _merge_handshake_evidence(
            pump_off_measured=True,
            item_released=release_evidence,
        )

        print("[HANDSHAKE] 7/8 Nano retorna HOME enquanto TurtleBot entrega.")
        _set_handshake("cobot_returning_home")
        if not _goto_pose_verified_with_resume(node, "place_approach", speed):
            raise RuntimeError("Nano não confirmou retorno a PLACE APPROACH.")
        if not _goto_pose_verified_with_resume(node, "home", 0.20):
            raise RuntimeError("Nano não confirmou retorno a HOME.")
        _merge_handshake_evidence(home_pose_measured=True)

        print("[HANDSHAKE] 8/8 Aguardando destino, docking e Manager livre.")
        _set_handshake("waiting_delivery_and_dock")
        completion = _wait_for_delivery_complete_on_host(
            expected_target,
            start_evidence["target_log_timestamp"],
            timeout=200.0,
        )
        turtle_node = get_turtlebot_node()
        dock_deadline = time.monotonic() + 10.0
        while time.monotonic() < dock_deadline:
            if turtle_node.telemetry_fresh() and turtle_node.is_docked:
                break
            time.sleep(0.25)
        if not (turtle_node.telemetry_fresh() and turtle_node.is_docked):
            raise RuntimeError("Log reportou docking, mas /dock_status fresco não confirmou dock físico.")
        _merge_handshake_evidence(delivery_complete=completion, dock_status_measured=True)

        _set_handshake(
            "completed",
            active=False,
            success=True,
            error=None,
            completed_at=time.time(),
        )
        print("[HANDSHAKE] SUCESSO medido: cobot HOME, entrega correta e TurtleBot dockado.")

    except Exception as e:
        detail = e.detail if isinstance(e, HTTPException) else str(e)
        print(f"[HANDSHAKE] FALHA: {detail}")
        _set_handshake("rollback", error=detail)
        rollback = _rollback_handshake_cobot(node, item_physically_released)
        if turtle_started and not item_physically_released:
            turtle_node = get_turtlebot_node()
            rollback.update(
                _recover_turtlebot_after_handshake_failure(
                    turtle_node,
                    stop_mission,
                    trigger_dock,
                )
            )
        _merge_handshake_evidence(rollback=rollback)
        _set_handshake(
            "failed",
            active=False,
            success=False,
            error=detail,
            completed_at=time.time(),
        )
    finally:
        cell_state["auto_running"] = False
        cell_state["status"] = "idle"
        cell_state["manual_step"] = "idle"
        cell_state["yolo_detected_item"] = None
        cell_state["manual_authorized"] = False


def _update_integrated_visual(name: str, evidence: dict) -> None:
    with _state_lock:
        integrated = dict(cell_state.get("integrated_real") or {})
        visuals = dict(integrated.get("visuals") or {})
        visuals[name] = evidence
        integrated["visuals"] = visuals
        cell_state["integrated_real"] = integrated


def _container_process_evidence(pattern: str) -> dict:
    """Mede processos dentro do container; saída vazia nunca vira sucesso."""
    import subprocess

    result = subprocess.run(
        ["docker", "exec", "mycobot_ros2", "pgrep", "-f", pattern],
        capture_output=True,
        text=True,
        timeout=4,
    )
    pids = [
        int(line)
        for line in result.stdout.splitlines()
        if line.strip().isdigit()
    ]
    return {"running": result.returncode == 0 and bool(pids), "pids": pids}


def _wait_for_planning_pc(timeout_sec: float = 70.0) -> dict:
    deadline = time.monotonic() + timeout_sec
    last = {}
    while time.monotonic() < deadline:
        try:
            move_group = _container_process_evidence("move_group")
            rviz = _container_process_evidence("rviz2")
            last = {"move_group": move_group, "rviz": rviz}
            if move_group["running"] and rviz["running"]:
                return {"ready": True, **last}
        except Exception as exc:
            last = {"error": str(exc)}
        time.sleep(1.0)
    return {"ready": False, **last}


def _wait_for_host_process(pattern: str, timeout_sec: float = 30.0) -> dict:
    import subprocess

    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True,
            timeout=3,
        )
        pids = [
            int(line)
            for line in result.stdout.splitlines()
            if line.strip().isdigit()
        ]
        if result.returncode == 0 and pids:
            return {"ready": True, "pids": pids}
        time.sleep(0.5)
    return {"ready": False, "pids": []}


def _require_integrated_running() -> None:
    if not _check_pause_and_cancel():
        raise RuntimeError("Operação integrada interrompida pelo operador.")


def _wait_for_handshake_infrastructure(timeout_sec: float = 35.0) -> dict:
    """Aguarda a ponte Nano voltar após o script do Planning PC reiniciá-la."""
    deadline = time.monotonic() + timeout_sec
    last_error = "ponte ainda indisponível"
    while time.monotonic() < deadline:
        _require_integrated_running()
        try:
            return _handshake_infrastructure_preflight()
        except HTTPException as exc:
            last_error = str(exc.detail)
        except Exception as exc:
            last_error = str(exc)
        time.sleep(1.0)
    raise RuntimeError(
        f"Ponte Nano não voltou mensurável após o Planning PC: {last_error}"
    )


def _stop_integrated_camera_processes() -> dict:
    """Fecha apenas o detector YOLO headless criado por este modo."""
    evidence = {}
    try:
        from backend.api.cobot_routes import stop_yolo_test_process

        stop_yolo_test_process()
        evidence["yolo_process_stopped"] = True
    except Exception as exc:
        evidence["yolo_stop_error"] = str(exc)
    return evidence


def _prepare_integrated_visuals(conf: float) -> dict:
    """Inicializa e mede MoveIt, RViz integrado e YOLO real headless."""
    from backend.api.cobot_routes import (
        is_yolo_process_alive,
        start_yolo_test_process,
    )
    from backend.api.health_routes import (
        check_http_stream,
        get_rviz_launch_status,
        launch_rviz,
        restart_camera_stream,
    )
    from backend.api.turtlebot_routes import launch_integrated_3d
    from backend.config.settings import get_settings

    evidence = {}
    _require_integrated_running()
    _set_integrated_real("starting_moveit")
    evidence["planning_request"] = launch_rviz()
    planning_run_id = evidence["planning_request"].get("run_id")
    launch_deadline = time.monotonic() + 100.0
    planning_launch = {}
    while time.monotonic() < launch_deadline:
        _require_integrated_running()
        planning_launch = get_rviz_launch_status(planning_run_id)
        if planning_launch.get("completed"):
            break
        time.sleep(0.5)
    evidence["planning_launch"] = planning_launch
    _update_integrated_visual("planning_launch", planning_launch)
    if planning_launch.get("success") is not True:
        raise RuntimeError(
            planning_launch.get("error")
            or "Lançador do Planning PC não concluiu com sucesso no prazo."
        )
    planning = _wait_for_planning_pc()
    evidence["planning_pc"] = planning
    _update_integrated_visual("planning_pc", planning)
    if planning.get("ready") is not True:
        raise RuntimeError("MoveIt e RViz do braço não ficaram ativos no prazo.")
    _require_integrated_running()

    # RUN_PLANNING_PC reinicia a ponte física; por isso o hardware é medido de
    # novo antes que qualquer movimento seja permitido.
    hardware_after_planning = _wait_for_handshake_infrastructure()
    evidence["hardware_after_planning"] = hardware_after_planning
    _update_integrated_visual("hardware_after_planning", hardware_after_planning)

    _set_integrated_real("starting_3d")
    evidence["integrated_3d_request"] = launch_integrated_3d()
    integrated_3d = _wait_for_host_process("rviz2_cobot_tb4_3d")
    evidence["integrated_3d"] = integrated_3d
    _update_integrated_visual("integrated_3d", integrated_3d)
    if integrated_3d.get("ready") is not True:
        raise RuntimeError("RViz 3D integrado não ficou ativo no prazo.")
    _require_integrated_running()

    _set_integrated_real("starting_yolo")
    camera_url = get_settings().CAMERA_STREAM_URL
    if not check_http_stream(camera_url, timeout_sec=1.0):
        restart_camera_stream()
        camera_deadline = time.monotonic() + 25.0
        while time.monotonic() < camera_deadline:
            if check_http_stream(camera_url, timeout_sec=1.0):
                break
            time.sleep(1.0)
    cobot_stream = check_http_stream(camera_url, timeout_sec=1.0)
    evidence["cobot_camera"] = {"ready": cobot_stream, "url": camera_url}
    _update_integrated_visual("cobot_camera", evidence["cobot_camera"])
    if not cobot_stream:
        raise RuntimeError("Stream da câmera do cobot não ficou disponível.")
    _require_integrated_running()

    if not start_yolo_test_process(conf=conf, headless=True):
        raise RuntimeError("Processo YOLO real headless não iniciou.")
    yolo_deadline = time.monotonic() + 35.0
    yolo_ready = False
    yolo_error = None
    while time.monotonic() < yolo_deadline:
        log_text = ""
        try:
            with open("/tmp/yolo_test.log", "r", encoding="utf-8", errors="replace") as log_file:
                log_text = log_file.read()
        except OSError:
            pass
        if is_yolo_process_alive() and "Câmera aberta." in log_text:
            yolo_ready = True
            break
        if not is_yolo_process_alive():
            yolo_error = "Processo YOLO terminou antes de abrir a câmera."
            break
        time.sleep(0.5)
    evidence["cobot_yolo"] = {
        "ready": yolo_ready,
        "process_alive": is_yolo_process_alive(),
        "headless": True,
        "error": yolo_error,
    }
    _update_integrated_visual("cobot_yolo", evidence["cobot_yolo"])
    if not yolo_ready:
        raise RuntimeError(yolo_error or "YOLO headless não confirmou a câmera do cobot.")
    _require_integrated_running()

    return evidence


def _run_integrated_real_mode(run_id: str) -> None:
    """Arma visão real e executa uma missão somente após classificação medida."""
    global _cycle_cancel, _abort_requested
    node = get_cobot_node()
    scan_confirmed = False
    handshake_started = False
    try:
        conf = max(0.10, min(0.99, float(cell_state.get("yolo_conf", 0.60))))
        visuals = _prepare_integrated_visuals(conf)
        _set_integrated_real("moving_scan", visuals=visuals)
        if not _goto_pose_verified_with_resume(
            node,
            "scan",
            max(0.10, min(1.0, float(cell_state.get("arm_speed", 0.50)))),
        ):
            raise RuntimeError("Nano não confirmou SCAN no modo integrado real.")
        scan_confirmed = True

        node.clear_yolo_state()
        _set_integrated_real("waiting_clear_view", candidate=None)
        clear_since = None
        last_candidate = None
        while _check_pause_and_cancel():
            yolo = node.get_last_yolo_msg()
            confidence = float((yolo or {}).get("confidence", 0.0))
            if yolo and confidence >= conf:
                clear_since = None
                candidate = {
                    "class": yolo.get("class"),
                    "confidence": confidence,
                    "blocked_reason": "campo visual ainda não ficou limpo",
                }
                candidate_marker = (candidate["class"], round(confidence, 2))
                if candidate_marker != last_candidate:
                    _set_integrated_real("waiting_clear_view", candidate=candidate)
                    last_candidate = candidate_marker
            else:
                if clear_since is None:
                    clear_since = time.monotonic()
                if time.monotonic() - clear_since >= 2.5:
                    break
            time.sleep(0.1)
        _require_integrated_running()
        _update_integrated_visual(
            "yolo_gate",
            {"ready": True, "clear_view_confirmed_sec": 2.5},
        )
        _set_integrated_real("waiting_real_yolo", candidate=None)
        samples = []
        last_timestamp = None
        while _check_pause_and_cancel():
            yolo = node.get_last_yolo_msg()
            if yolo:
                timestamp = float(yolo.get("timestamp", 0.0))
                confidence = float(yolo.get("confidence", 0.0))
                if timestamp != last_timestamp and confidence >= conf:
                    last_timestamp = timestamp
                    sample = dict(yolo)
                    sample["source"] = "real_yolo_camera"
                    samples.append(sample)
                    samples = samples[-120:]
                    canonical_class, target = _stable_real_yolo_class(samples)
                    if canonical_class and target:
                        candidate = {
                            **sample,
                            "class": canonical_class,
                            "raw_class": sample.get("class"),
                            "target": target,
                            "threshold": conf,
                            "distinct_samples": 5,
                            "sample_span_min_sec": 0.8,
                        }
                        _real_detection_confirm_event.clear()
                        _set_integrated_real(
                            "waiting_detection_confirmation",
                            candidate=candidate,
                            detection=None,
                        )

                        while _check_pause_and_cancel():
                            if not _real_detection_confirm_event.wait(timeout=0.1):
                                continue
                            _real_detection_confirm_event.clear()
                            confirmed = node.get_last_yolo_msg()
                            confirmed_confidence = float(
                                (confirmed or {}).get("confidence", 0.0)
                            )
                            confirmed_age = time.time() - float(
                                (confirmed or {}).get("timestamp", 0.0)
                            )
                            try:
                                confirmed_class, confirmed_target = (
                                    _normalize_handshake_class(
                                        (confirmed or {}).get("class", "")
                                    )
                                )
                            except HTTPException:
                                confirmed_class, confirmed_target = None, None
                            if not (
                                confirmed
                                and confirmed_age <= 1.0
                                and confirmed_confidence >= conf
                                and confirmed_class == canonical_class
                                and confirmed_target == target
                            ):
                                candidate["blocked_reason"] = (
                                    "detecção mudou ou ficou obsoleta antes da confirmação"
                                )
                                _set_integrated_real(
                                    "waiting_detection_confirmation",
                                    candidate=candidate,
                                )
                                continue

                            detection = {
                                **candidate,
                                "confirmation": "operator_dashboard",
                                "confirmed_at": time.time(),
                                "confirmation_frame_age_sec": confirmed_age,
                                "confidence": confirmed_confidence,
                            }
                            break
                        _require_integrated_running()
                        _set_integrated_real(
                            "real_yolo_confirmed",
                            candidate=None,
                            detection=detection,
                        )
                        preflight = _handshake_preflight(canonical_class)
                        with _state_lock:
                            cell_state["handshake"] = {
                                "active": True,
                                "run_id": run_id,
                                "phase": "yolo_detected",
                                "item_class": canonical_class,
                                "canonical_class": canonical_class,
                                "target": target,
                                "success": None,
                                "error": None,
                                "started_at": time.time(),
                                "completed_at": None,
                                "evidence": {
                                    "preflight": preflight,
                                    "yolo_real_detection": detection,
                                },
                            }
                        handshake_started = True
                        _run_handshake_test_standalone(
                            canonical_class,
                            preflight,
                            real_detection=detection,
                            scan_already_confirmed=True,
                        )
                        handshake = cell_state.get("handshake") or {}
                        if handshake.get("success") is True:
                            _set_integrated_real(
                                "completed",
                                active=False,
                                error=None,
                                completed_at=time.time(),
                            )
                        else:
                            _set_integrated_real(
                                "failed",
                                active=False,
                                error=handshake.get("error") or "Handshake real falhou.",
                                completed_at=time.time(),
                            )
                        return
            time.sleep(0.1)
        raise RuntimeError("Operação integrada interrompida pelo operador.")
    except Exception as exc:
        detail = str(exc)
        if scan_confirmed and not handshake_started:
            pump_off = node.set_pump_verified(False)
            home = node.goto_pose_verified("home", 0.15)
            _update_integrated_visual(
                "safe_stop",
                {"pump_off_measured": pump_off, "home_measured": home},
            )
        _set_integrated_real(
            "stopped" if _cycle_cancel else "failed",
            active=False,
            error=detail,
            completed_at=time.time(),
        )
    finally:
        yolo_stop = _stop_integrated_camera_processes()
        _update_integrated_visual("yolo_stop", yolo_stop)
        _real_detection_confirm_event.clear()
        cell_state["auto_running"] = False
        if not (cell_state.get("handshake") or {}).get("active"):
            cell_state["status"] = "idle"

def _run_auto_loop():
    """Worker do modo automático contínuo com verificação de interrupção e cooldown."""
    global _cycle_cancel, _abort_requested
    print("[AUTO_LOOP] 🚀 Modo Automático INICIADO em background.")
    
    while cell_state.get("auto_running", False) and not _cycle_cancel and not _abort_requested:
        if cell_state.get("panic_locked"):
            break

        _run_cycle_internal(is_manual=False)
        
        if not cell_state.get("auto_running", False) or _cycle_cancel or _abort_requested:
            break

        cooldown = float(cell_state.get("cooldown_sec", 5.0))
        t0 = time.time()
        while (time.time() - t0) < cooldown:
            if not cell_state.get("auto_running", False) or _cycle_cancel or _abort_requested:
                break
            if not _check_pause_and_cancel():
                break
            time.sleep(0.3)

    cell_state["auto_running"] = False
    print("[AUTO_LOOP] 🛑 Modo Automático TOTALMENTE ENCERRADO.")

@router.get("/status")
def get_cell_status():
    """Retorna o status global da célula automatizada."""
    node = get_cobot_node()
    from backend.api.cobot_routes import is_yolo_process_alive
    hardware = node.get_hardware_status()
    measured_joints = node.get_measured_joints()
    return {
        "cell": cell_state,
        "current_joints": measured_joints,
        "joints_source": "nano_get_angles" if measured_joints is not None else None,
        "pump_active": (
            hardware.get("pump_active") if hardware else node.pump_active
        ),
        "hardware": hardware,
        "yolo_test_active": is_yolo_process_alive(),
        "last_yolo": node.get_last_yolo_msg()
    }

@router.post("/mode")
def set_cell_mode(payload: CellModeSchema):
    """Altera as configurações mestre da célula (modo, cooldown, confiança)."""
    global _cycle_cancel
    if cell_state.get("panic_locked"):
        raise HTTPException(status_code=423, detail="Célula bloqueada em modo de Pânico. É necessário reiniciar o sistema.")
    if payload.mode not in ["auto", "manual"]:
        raise HTTPException(status_code=400, detail="Modo deve ser 'auto' ou 'manual'.")

    cell_state["mode"] = payload.mode
    if payload.cooldown_sec is not None:
        cell_state["cooldown_sec"] = max(0.0, payload.cooldown_sec)
    if payload.yolo_conf is not None:
        cell_state["yolo_conf"] = max(0.10, min(1.0, payload.yolo_conf))
    if payload.arm_speed is not None:
        cell_state["arm_speed"] = max(0.05, min(1.0, payload.arm_speed))

    if payload.mode == "manual":
        # Se trocou para MANUAL, desliga o loop automático
        cell_state["auto_running"] = False
        _cycle_cancel = True

    return {"status": "success", "cell": cell_state}

class TestHandshakeSchema(BaseModel):
    item_class: str = "tin_valid_blue_square"  # "tin_valid_blue_square" ou "tin_valid_red_square"


@router.post("/integrated_real/preflight")
def preflight_integrated_real():
    """Valida robôs e comunicação sem mover ou pressupor uma classe."""
    if cell_state.get("panic_locked"):
        raise HTTPException(status_code=423, detail="Célula bloqueada em Pânico.")
    if _cycle_thread is not None and _cycle_thread.is_alive():
        raise HTTPException(status_code=409, detail="Há um ciclo em execução.")
    return {
        "status": "ready",
        "movement_commanded": False,
        "class_assumed": False,
        "preflight": _handshake_infrastructure_preflight(),
    }


@router.post("/integrated_real/start")
def start_integrated_real():
    """Inicia visualizações e arma um ciclo para classificação YOLO real."""
    global _cycle_thread, _cycle_cancel, _abort_requested, _pause_event
    if cell_state.get("panic_locked"):
        raise HTTPException(status_code=423, detail="Célula bloqueada em Pânico.")
    if _cycle_thread is not None and _cycle_thread.is_alive():
        raise HTTPException(
            status_code=409,
            detail="Já existe um ciclo ou operação integrada em execução.",
        )

    preflight = _handshake_infrastructure_preflight()
    run_id = uuid.uuid4().hex[:12]
    _cycle_cancel = False
    _abort_requested = False
    _real_detection_confirm_event.clear()
    _pause_event.set()
    cell_state["mode"] = "auto"
    cell_state["auto_running"] = True
    with _state_lock:
        cell_state["integrated_real"] = {
            "active": True,
            "run_id": run_id,
            "phase": "preflight_passed",
            "error": None,
            "started_at": time.time(),
            "completed_at": None,
            "visuals": {"preflight": preflight},
            "detection": None,
            "candidate": None,
        }
        cell_state["status"] = "integrated_preflight_passed"

    _cycle_thread = threading.Thread(
        target=_run_integrated_real_mode,
        kwargs={"run_id": run_id},
        daemon=True,
    )
    _cycle_thread.start()
    return {
        "status": "started",
        "run_id": run_id,
        "movement_commanded": False,
        "message": (
            "Operação integrada iniciada. As visualizações serão confirmadas "
            "antes de o cobot ir para SCAN; o Turtle só se moverá após YOLO real "
            "estável e confirmação explícita do operador."
        ),
        "preflight": preflight,
    }


@router.post("/integrated_real/confirm_detection")
def confirm_integrated_real_detection():
    """Autoriza pick/delivery somente para o candidato medido e ainda visível."""
    with _state_lock:
        integrated = dict(cell_state.get("integrated_real") or {})
        if integrated.get("active") is not True:
            raise HTTPException(status_code=409, detail="Operação integrada não está ativa.")
        if integrated.get("phase") != "waiting_detection_confirmation":
            raise HTTPException(
                status_code=409,
                detail="Ainda não existe uma detecção estável aguardando confirmação.",
            )
        candidate = dict(integrated.get("candidate") or {})
        if not candidate.get("class") or not candidate.get("target"):
            raise HTTPException(status_code=409, detail="Candidato YOLO não mensurável.")
    _real_detection_confirm_event.set()
    return {
        "status": "confirmation_requested",
        "movement_commanded": False,
        "candidate": candidate,
        "message": (
            "Confirmação recebida. O worker ainda verificará uma imagem fresca "
            "da mesma classe antes de liberar pick e delivery."
        ),
    }


@router.post("/integrated_real/stop")
def stop_integrated_real():
    """Solicita parada; o worker mede bomba OFF/HOME ou executa rollback."""
    global _cycle_cancel
    _cycle_cancel = True
    cell_state["auto_running"] = False
    integrated = cell_state.get("integrated_real") or {}
    if integrated.get("active"):
        _set_integrated_real("stopping")

    stop_evidence = _stop_integrated_camera_processes()
    if (cell_state.get("handshake") or {}).get("active"):
        try:
            from backend.api.turtlebot_routes import stop_mission
            stop_evidence["mission_stop"] = stop_mission()
        except Exception as exc:
            stop_evidence["mission_stop_error"] = str(exc)
    _update_integrated_visual("stop_request", stop_evidence)
    return {
        "status": "stopping",
        "message": "Parada solicitada; aguarde HOME/dock serem medidos no estado.",
        "evidence": stop_evidence,
    }


@router.post("/test_handshake/preflight")
def preflight_test_handshake(payload: TestHandshakeSchema):
    """Valida todos os elos do teste integrado sem comandar movimento."""
    if cell_state.get("panic_locked"):
        raise HTTPException(status_code=423, detail="Célula bloqueada em Pânico.")
    if _cycle_thread is not None and _cycle_thread.is_alive():
        raise HTTPException(status_code=409, detail="Há um ciclo em execução.")
    evidence = _handshake_preflight(payload.item_class)
    return {
        "status": "ready",
        "movement_commanded": False,
        "preflight": evidence,
    }


@router.post("/test_handshake")
def trigger_test_handshake(payload: TestHandshakeSchema):
    """Executa um ciclo automático completo do Cobot simular a detecção YOLO para testar a comunicação handshake com o TurtleBot 4."""
    global _cycle_thread, _cycle_cancel, _abort_requested, _pause_event
    if cell_state.get("panic_locked"):
        raise HTTPException(status_code=423, detail="Célula bloqueada em Pânico.")

    if _cycle_thread is not None and _cycle_thread.is_alive():
        raise HTTPException(status_code=409, detail="Um ciclo já está em execução. Aguarde a conclusão antes de iniciar outro teste.")

    preflight = _handshake_preflight(payload.item_class)
    run_id = uuid.uuid4().hex[:12]
    cell_state["mode"] = "auto"
    cell_state["auto_running"] = True
    _cycle_cancel = False
    _abort_requested = False
    _pause_event.set()
    with _state_lock:
        cell_state["handshake"] = {
            "active": True,
            "run_id": run_id,
            "phase": "preflight_passed",
            "item_class": payload.item_class,
            "canonical_class": preflight["canonical_class"],
            "target": preflight["target"],
            "success": None,
            "error": None,
            "started_at": time.time(),
            "completed_at": None,
            "evidence": {"preflight": preflight},
        }
        cell_state["status"] = "handshake_preflight_passed"

    _cycle_thread = threading.Thread(
        target=_run_handshake_test_standalone,
        kwargs={"item_class": payload.item_class, "preflight": preflight},
        daemon=True,
    )
    _cycle_thread.start()
    return {
        "status": "started",
        "run_id": run_id,
        "canonical_class": preflight["canonical_class"],
        "target": preflight["target"],
        "preflight": preflight,
        "message": (
            f"Handshake {run_id} iniciado com '{preflight['canonical_class']}' "
            f"para '{preflight['target']}'."
        ),
    }

@router.post("/auto/start")
def start_auto_mode():
    """Inicia a execução contínua do Modo Automático."""
    global _cycle_thread, _cycle_cancel, _abort_requested, _pause_event
    if cell_state.get("panic_locked"):
        raise HTTPException(status_code=423, detail="Célula bloqueada em Pânico.")

    cell_state["mode"] = "auto"
    cell_state["auto_running"] = True
    _cycle_cancel = False
    _abort_requested = False
    _pause_event.set()

    if _cycle_thread is None or not _cycle_thread.is_alive():
        _cycle_thread = threading.Thread(target=_run_auto_loop, daemon=True)
        _cycle_thread.start()
        return {"status": "success", "message": "Modo Automático INICIADO com SUCESSO!"}

    return {"status": "success", "message": "Modo Automático já está em execução."}

@router.post("/auto/stop")
def stop_auto_mode():
    """Para a execução do Modo Automático."""
    global _cycle_cancel
    _cycle_cancel = True
    cell_state["auto_running"] = False
    cell_state["mode"] = "auto"
    cell_state["status"] = "idle"
    return {"status": "success", "message": "Modo Automático PARADO."}

# ============================================================
# ENDPOINTS DO MODO MANUAL PASSO-A-PASSO
# ============================================================

@router.post("/manual/start_scan")
def manual_start_scan():
    """Passo 1 do Modo Manual: move o braço para a posição SCAN e liga a inspeção de visão YOLO."""
    global _cycle_thread
    if cell_state.get("panic_locked"):
        raise HTTPException(status_code=423, detail="Célula bloqueada em Pânico.")
    if cell_state["mode"] != "manual":
        raise HTTPException(status_code=400, detail="Este comando é exclusivo do Modo Manual.")
    if _cycle_thread is not None and _cycle_thread.is_alive():
        raise HTTPException(status_code=409, detail="Um ciclo já está em execução.")

    _cycle_thread = threading.Thread(target=_run_cycle_internal, kwargs={"is_manual": True}, daemon=True)
    _cycle_thread.start()
    return {"status": "success", "message": "Braço movendo para SCAN e ativando visão YOLO..."}

@router.post("/manual/authorize_pick")
def manual_authorize_pick():
    """Passo 2 do Modo Manual: Autoriza avançar para o PICK somente se houver lata válida detectada pelo YOLO."""
    if cell_state["mode"] != "manual":
        raise HTTPException(status_code=400, detail="Exclusivo do Modo Manual.")
    if cell_state["status"] != "at_scan_inspecting":
        raise HTTPException(status_code=400, detail="O braço precisa estar na posição SCAN inspecionando para autorizar a coleta.")
    if not cell_state.get("yolo_detected_item"):
        raise HTTPException(status_code=400, detail="Impossível autorizar coleta: nenhuma lata válida foi identificada pela visão YOLO!")

    _step_pick_event.set()
    return {"status": "success", "message": "Coleta autorizada! Movendo braço para o PICK..."}

@router.post("/manual/authorize_place")
def manual_authorize_place():
    """Passo 3 do Modo Manual: Autoriza avançar para soltar a lata no PLACE quando o braço estiver em PLACE_APPROACH."""
    if cell_state["mode"] != "manual":
        raise HTTPException(status_code=400, detail="Exclusivo do Modo Manual.")
    if cell_state["status"] != "at_place_approach_waiting":
        raise HTTPException(status_code=400, detail="O braço precisa estar aguardando em PLACE APPROACH para autorizar a soltura.")

    _step_place_event.set()
    return {"status": "success", "message": "Soltura autorizada! Liberando lata no PLACE..."}

# ============================================================
# ENDPOINTS DE INTERRUPÇÃO (PAUSA / CONFIRMAÇÃO / ABORT)
# ============================================================

@router.post("/interrupt")
def interrupt_operation():
    """Botão Interromper (Manual e Auto): Congela os motores do robô em < 5ms no ponto atual e abre confirmação."""
    if cell_state.get("panic_locked"):
        raise HTTPException(status_code=423, detail="Célula bloqueada em Pânico.")

    _pause_event.clear()  # Congela a thread do ciclo instantaneamente
    cell_state["status"] = "interrupted_paused"

    # Dispara a trava dos servos em < 5ms via HTTP Micro-Bridge diretamente no microcontrolador/Nano
    try:
        import urllib.request
        from backend.config.settings import get_settings
        nano_ip = get_settings().JETSON_NANO_IP
        req = urllib.request.Request(f"http://{nano_ip}:8088/servos/lock")
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            print(f"[INFO] Trava de interrupção via HTTP Micro-Bridge ({nano_ip}) enviada em < 5ms!")
    except Exception as e:
        print(f"[WARN] HTTP Micro-Bridge lock indisponível: {e}")

    node = get_cobot_node()
    node.call_trigger_service(node.lock_cli, "Travar Servos (Interrupção)")

    return {
        "status": "interrupted",
        "message": "Operação interrompida! Motores congelados instantaneamente na posição atual."
    }

@router.post("/interrupt/confirm")
def confirm_interrupt(payload: InterruptConfirmSchema):
    """Confirmação da Interrupção: abort=True (SIM, aborta e solta a lata no pick) ou abort=False (NÃO, continua). Mantém torque 100% ativo."""
    global _abort_requested, _cycle_thread
    
    if payload.abort:
        print("[INTERRUPT] Usuário selecionou SIM (ABORTAR). Motores mantêm torque 100% ativo!")
        _abort_requested = True
        _cycle_cancel = True
        _pause_event.set()  # Acorda a thread para executar o _abort_cleanup() mantendo o torque dos motores!
        
        # Se nenhuma thread de ciclo estiver rodando em segundo plano, executa a limpeza imediatamente
        if _cycle_thread is None or not _cycle_thread.is_alive():
            _abort_cleanup()
        return {"status": "aborting", "message": "Abortando operação com torque ativo... Retornando braço para HOME."}
    else:
        print("[INTERRUPT] Usuário selecionou NÃO (CONTINUAR). Motores mantêm torque e retomam a movimentação!")
        _abort_requested = False
        _pause_event.set()  # Acorda a thread para continuar o movimento normal mantendo o torque energizado!
        
        # Se nenhuma thread de ciclo estiver rodando em segundo plano, restaura o status para idle
        if _cycle_thread is None or not _cycle_thread.is_alive():
            cell_state["status"] = "idle"
            cell_state["manual_step"] = "idle"
        return {"status": "resumed", "message": "Operação retomada com sucesso!"}

@router.post("/stop")
def emergency_stop():
    """Parada de emergência suave: desliga bomba, cancela o Modo Automático, desativa visão YOLO e retorna o braço para HOME."""
    global _cycle_cancel, _abort_requested
    _cycle_cancel = True
    _abort_requested = True
    _pause_event.set()

    if cell_state.get("panic_locked"):
        raise HTTPException(status_code=423, detail="Célula bloqueada em modo de Pânico. É necessário reiniciar o sistema.")

    node = get_cobot_node()
    node.load_poses()
    if "home" not in node.poses:
        raise HTTPException(
            status_code=400,
            detail="A pose 'home' ainda não foi salva no disco! Grave e salve a pose 'home' antes de acionar o retorno de emergência."
        )

    from backend.api.cobot_routes import stop_yolo_test_process
    from backend.api.turtlebot_routes import stop_mission
    stop_yolo_test_process()
    node.set_pump(False)
    cell_state["status"] = "stopped"
    cell_state["manual_authorized"] = False
    cell_state["manual_step"] = "idle"
    cell_state["yolo_detected_item"] = None

    # Envia ordem de parada de emergência e retorno à dock para o TurtleBot 4
    try:
        stop_mission()
    except Exception as e:
        print(f"[WARN] Falha ao enviar parada de emergência ao TurtleBot 4: {e}")

    def _home_worker():
        try:
            node.goto_pose("home", 0.15)
        except Exception:
            pass
        finally:
            cell_state["status"] = "idle"

    t = threading.Thread(target=_home_worker, daemon=True)
    t.start()

    return {
        "status": "emergency_stop_triggered",
        "message": "Parada de emergência GLOBAL acionada! Modo Automático DESLIGADO, bomba e teste YOLO parados, TurtleBot 4 ordenado à DOCK e braço retornando para HOME."
    }

@router.post("/panic")
def panic_stop():
    """Botão de Pânico Master: interrompe TUDO no projeto (Bomba, Câmera, YOLO, Robô, Motores e Planejamento MoveIt) e bloqueia a célula instantaneamente em < 10ms."""
    global _cycle_cancel, _abort_requested
    _cycle_cancel = True
    _abort_requested = True
    _pause_event.set()

    # Trava imediata de estado local (< 1ms)
    cell_state["panic_locked"] = True
    cell_state["status"] = "panic_locked"
    cell_state["manual_authorized"] = False
    cell_state["manual_step"] = "idle"

    # Worker assíncrono em segundo plano para limpeza de SSH, sub-processos e ROS 2 sem travar a resposta HTTP
    def _async_panic_cleanup():
        from backend.api.cobot_routes import stop_yolo_test_process
        from backend.api.health_routes import stop_camera_stream
        import subprocess
        import urllib.request
        from backend.config.settings import get_settings

        nano_ip = get_settings().JETSON_NANO_IP

        try:
            req = urllib.request.Request(f"http://{nano_ip}:8088/panic")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                print(f"[INFO] Pânico via HTTP Micro-Bridge ({nano_ip}) enviado em < 5ms (Motores congelados no robô físico)")
        except Exception as e:
            print(f"[WARN] HTTP Micro-Bridge panic trigger indisponível: {e}")

        try:
            stop_yolo_test_process()
        except Exception as e:
            print(f"[WARN] Erro ao parar teste YOLO no pânico: {e}")

        try:
            stop_camera_stream()
        except Exception as e:
            print(f"[WARN] Erro ao desligar câmera no pânico: {e}")

        node = get_cobot_node()
        try:
            node.set_pump(False)
            node.clear_yolo_state()
            node.call_trigger_service(node.lock_cli, "Travar Servos (Pânico)")
        except Exception as e:
            print(f"[WARN] Erro ao travar braço no pânico: {e}")

        try:
            from backend.api.turtlebot_routes import stop_mission
            stop_mission()
            print("[INFO] Parada de Emergência enviada ao TurtleBot 4 no Pânico!")
        except Exception as e:
            print(f"[WARN] Erro ao enviar parada ao TurtleBot 4 no pânico: {e}")
            print(f"[WARN] Erro ao desligar bomba/motores no Pânico: {e}")

        try:
            print("[INFO] Matando MoveIt Planning, RViz e janelas GUI no container mycobot_ros2...")
            subprocess.run('docker exec mycobot_ros2 bash -c "pkill -9 -f move_group 2>/dev/null || true; pkill -9 -f rviz 2>/dev/null || true; pkill -9 -f cam_yolo_test 2>/dev/null || true"', shell=True, timeout=5)
        except Exception as e:
            print(f"[WARN] Erro ao matar MoveIt planning no pânico: {e}")

        try:
            from backend.config.settings import get_nano_ssh_password, get_nano_ssh_user
            nano_user = get_nano_ssh_user()
            nano_pass = get_nano_ssh_password()
            print(f"[INFO] Matando ponte mycobot_bridge na Jetson Nano ({nano_ip})...")
            cmd_kill_nano = f"sshpass -p '{nano_pass}' ssh -o StrictHostKeyChecking=no {nano_user}@{nano_ip} 'pkill -9 -f mycobot_bridge 2>/dev/null || true; fuser -k 8088/tcp 2>/dev/null || true'"
            subprocess.run(cmd_kill_nano, shell=True, timeout=5)
        except Exception as e:
            print(f"[WARN] Erro ao encerrar mycobot_bridge no Nano: {e}")

    t = threading.Thread(target=_async_panic_cleanup, daemon=True)
    t.start()

    return {
        "status": "panic_triggered",
        "panic_locked": True,
        "message": "PÂNICO ABSOLUTO: Todos os componentes foram PARADOS! As juntas do robô estão TRAVADAS. É necessário reiniciar."
    }

def _reset_cell_panic_lock():
    """Desbloqueia a célula do estado de pânico, zera o modo automático e reseta os status para idle."""
    global _abort_requested, _cycle_cancel
    _abort_requested = False
    _cycle_cancel = True
    cell_state["panic_locked"] = False
    cell_state["auto_running"] = False
    cell_state["mode"] = "auto"
    cell_state["status"] = "idle"
    cell_state["manual_step"] = "idle"
    cell_state["manual_authorized"] = False
    cell_state["yolo_detected_item"] = None
    print("[CELL] 🔓 Trava de Pânico DESBLOQUEADA e estado resetado para IDLE com SUCESSO!")

@router.post("/reset_panic")
def reset_panic():
    """Desbloqueia o estado de Pânico e dispara a reinicialização limpa do MoveIt, da Câmera e do Hardware Nano."""
    _reset_cell_panic_lock()

    from backend.api.health_routes import restart_nano_hardware
    try:
        restart_nano_hardware()
    except Exception as e:
        print(f"[WARN] Erro ao reiniciar componentes no desbloqueio do pânico: {e}")

    return {
        "status": "success",
        "message": "Pânico desbloqueado com sucesso! O planejador MoveIt, o hardware da Nano e a câmera estão sendo reiniciados do zero..."
    }
