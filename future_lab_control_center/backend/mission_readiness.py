"""Regras puras de prontidão para missões autônomas do TurtleBot 4."""


def mission_readiness(checks: dict) -> dict:
    """Calcula a prontidão para iniciar uma missão autônoma.

    A prontidão de navegação direta exige LaserScan e AMCL frescos. Uma missão
    iniciada na dock tem outro contrato: ela própria executa o undock e só
    envia o primeiro goal depois de confirmar scan, odometria e TF. Quando o
    robô já está fora da dock, esses sinais frescos são obrigatórios.
    """
    start_mode = "docked" if checks.get("undocked") is False else "undocked"
    # A Create 3 deliberadamente deixa de publicar odom->base_link e o TB4
    # desliga o motor do RPLidar quando está acoplado. Exigi-los antes de
    # aceitar uma missão dockada cria um impasse: a rotina que deveria fazer
    # o undock nunca chega a ser chamada. Ainda exigimos telemetria fresca
    # (create3_alive), as duas ações nativas e Nav2 já ativo; odometria,
    # laser e AMCL passam a ser obrigatórios somente quando o robô já está
    # fora da dock. A MissionBase mede esses sinais novamente após undock
    # antes de enviar qualquer meta de navegação.
    nav2_paused_standby = (
        start_mode == "docked"
        and checks.get("nav2_paused_standby") is True
    )
    required = [
        "create3_alive",
        "map",
        "create3_dock_action",
        "create3_undock_action",
        "start_delivery",
        "stop_mission",
    ]
    if nav2_paused_standby:
        # PAUSE desativa os servidores para impedir que costmaps consultem TF
        # que a Create 3 deixa de publicar na dock. O processo e o lifecycle
        # manager continuam medidos; MissionBase faz RESUME após o undock e
        # antes de qualquer meta. Isso não equivale a navegação direta pronta.
        required.append("nav2_paused_standby")
    else:
        required.extend(["navigate_to_pose", "global_costmap"])
    if start_mode == "undocked":
        required.extend(["odom", "scan", "amcl_pose"])

    missing = [name for name in required if checks.get(name) is not True]
    if not missing and start_mode == "docked":
        if nav2_paused_standby:
            hint = (
                "Missão pronta a partir do Nav2 pausado na dock. A rotina fará "
                "undock, RESUME da mesma geração Nav2 e validará scan, odometria "
                "e TF antes do primeiro goal."
            )
        else:
            hint = (
                "Missão pronta para iniciar na dock. A rotina fará o undock e "
                "validará scan, odometria e TF antes do primeiro goal."
            )
    elif not missing:
        hint = "Missão pronta para iniciar com o robô fora da dock."
    else:
        hint = "Missão bloqueada pelos itens listados em mission_missing."

    return {
        "ready": not missing,
        "missing": missing,
        "required": required,
        "start_mode": start_mode,
        "hint": hint,
    }
