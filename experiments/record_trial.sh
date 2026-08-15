#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="/home/future-lab/B002_Future_Lab_Bots"
EXPERIMENT_ROOT="${B002_EXPERIMENT_ROOT:-/home/future-lab/B002_experiment_data}"
API_URL="${B002_API_URL:-http://127.0.0.1:8000}"
CAMERA_URL="${B002_CAMERA_URL:-http://192.168.0.62:8080/stream.mjpg}"
condition=""
run=""
can_color=""
campaign="campaign_$(date -u +%Y%m%d)"
operator_name=""
notes=""
mode="real"
capture_video=1
duration=10

usage() {
  echo "Uso: $0 --condition no_obstacle|static_obstacle|dynamic_obstacle --run 1..20 --can blue|red [--campaign ID] [--operator NOME] [--notes TEXTO] [--no-video]"
  echo "Smoke sem movimento: $0 --smoke [--duration 10] [--campaign ID]"
}

while (($#)); do
  case "$1" in
    --condition) condition="$2"; shift 2 ;;
    --run) run="$2"; shift 2 ;;
    --can) can_color="$2"; shift 2 ;;
    --campaign) campaign="$2"; shift 2 ;;
    --operator) operator_name="$2"; shift 2 ;;
    --notes) notes="$2"; shift 2 ;;
    --no-video) capture_video=0; shift ;;
    --smoke) mode="smoke"; condition="smoke"; run="0"; can_color="none"; capture_video=0; shift ;;
    --duration) duration="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Argumento desconhecido: $1"; usage; exit 2 ;;
  esac
done

if [[ "$mode" == real ]]; then
  [[ "$condition" =~ ^(no_obstacle|static_obstacle|dynamic_obstacle)$ ]] || { usage; exit 2; }
  [[ "$run" =~ ^([1-9]|1[0-9]|20)$ ]] || { usage; exit 2; }
  [[ "$can_color" =~ ^(blue|red)$ ]] || { usage; exit 2; }
fi
[[ "$duration" =~ ^[0-9]+$ ]] || { echo "--duration deve ser inteiro"; exit 2; }

mkdir -p "$EXPERIMENT_ROOT/$campaign/trials"
exec 9>"$EXPERIMENT_ROOT/.record_trial.lock"
flock -n 9 || { echo "ERRO: já existe um gravador de ensaio ativo."; exit 1; }

set +u
source /opt/ros/jazzy/setup.bash
source "$PROJECT_ROOT/turtlebot4_jazzy/setup.bash"
set -u
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_SUPER_CLIENT=True
export ROS_DISCOVERY_SERVER="192.168.0.129:11811;"
unset FASTDDS_BUILTIN_TRANSPORTS
unset ROS_AUTOMATIC_DISCOVERY_RANGE

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
started_at_utc="$(date -u +%FT%TZ)"
trial_id="trial_$(printf '%03d' "$run")_${condition}_rep$(printf '%02d' "$run")_${can_color}_${timestamp}"
trial_dir="$EXPERIMENT_ROOT/$campaign/trials/$trial_id"
mkdir -p "$trial_dir/api_initial" "$trial_dir/api_final" "$trial_dir/logs" "$trial_dir/ros_logs"
export ROS_LOG_DIR="$trial_dir/ros_logs"

log_sources=(/tmp/nav2_mission_manager.log /tmp/nav2_stack.log /tmp/nav2_localization.log /tmp/future_lab_host_agent.log)
for log_source in "${log_sources[@]}"; do
  if [[ -f "$log_source" ]]; then
    printf '%s\t%s\n' "$log_source" "$(stat -c %s "$log_source")" >> "$trial_dir/log_offsets.tsv"
  fi
done

curl -fsS "$API_URL/api/v1/cell/status" -o "$trial_dir/api_initial/cell_status.json" || { echo "ERRO: backend não responde."; exit 1; }
curl -fsS "$API_URL/api/v1/turtlebot/status" -o "$trial_dir/api_initial/turtlebot_status.json"
curl -fsS "$API_URL/api/v1/turtlebot/nav_readiness" -o "$trial_dir/api_initial/nav_readiness.json"
curl -fsS "$API_URL/api/v1/turtlebot/processes" -o "$trial_dir/api_initial/processes.json"
curl -fsS "$API_URL/api/v1/health/" -o "$trial_dir/api_initial/health.json"

if [[ "$mode" == real ]]; then
  jq -e '.telemetry_ok == true and .is_docked == true' "$trial_dir/api_initial/turtlebot_status.json" >/dev/null || { echo "ERRO: TurtleBot sem telemetria fresca ou fora da dock."; exit 1; }
  jq -e '.mission_ready == true' "$trial_dir/api_initial/nav_readiness.json" >/dev/null || { echo "ERRO: mission_ready não está verdadeiro."; exit 1; }
  jq -e '(.cell.handshake.active == false) and (.cell.integrated_real.active == false)' "$trial_dir/api_initial/cell_status.json" >/dev/null || { echo "ERRO: workflow já está ativo ou estado não foi medido."; exit 1; }
  jq -e '(.pump_active == false) and (.hardware.success == true) and (.hardware.mock == false)' "$trial_dir/api_initial/cell_status.json" >/dev/null || { echo "ERRO: Cobot real não medido como pronto ou bomba não está desligada."; exit 1; }
  jq -e '.devices.jetson_nano.camera_stream_online == true' "$trial_dir/api_initial/health.json" >/dev/null || { echo "ERRO: stream da câmera do Cobot não está online."; exit 1; }
fi

available_topics="$(ros2 topic list)"
printf '%s\n' "$available_topics" > "$trial_dir/topics_at_start.txt"
ros2 node list > "$trial_dir/nodes_at_start.txt"
for required in /odom /dock_status /joint_states /future_lab/events; do
  grep -Fxq "$required" <<<"$available_topics" || { echo "ERRO DDS: tópico mínimo ausente: $required"; exit 1; }
done

free_kb="$(df --output=avail "$EXPERIMENT_ROOT" | tail -1 | tr -d ' ')"
(( free_kb >= 10485760 )) || { echo "ERRO: menos de 10 GiB livres em $EXPERIMENT_ROOT"; exit 1; }

git_commit="$(git -C "$PROJECT_ROOT" rev-parse HEAD)"
git_dirty=false
git -C "$PROJECT_ROOT" diff --quiet --ignore-submodules=none || git_dirty=true
jq -n --arg trial_id "$trial_id" --arg campaign "$campaign" --arg condition "$condition" \
  --arg run "$run" --arg can "$can_color" --arg operator "$operator_name" --arg notes "$notes" \
  --arg started_at "$started_at_utc" --arg host "$(hostname)" --arg commit "$git_commit" \
  --argjson git_dirty "$git_dirty" --arg mode "$mode" \
  '{schema:"future_lab.trial.v1",trial_id:$trial_id,campaign:$campaign,condition:$condition,replicate:$run,can_color:$can,operator:$operator,notes:$notes,started_at_utc:$started_at,host:$host,git_commit:$commit,git_dirty:$git_dirty,mode:$mode}' \
  > "$trial_dir/trial.json"

python3 "$PROJECT_ROOT/experiments/sample_dashboard_state.py" --api "$API_URL" --output "$trial_dir/dashboard_state.jsonl" &
sampler_pid=$!
python3 "$PROJECT_ROOT/experiments/event_relay.py" \
  --input "$PROJECT_ROOT/future_lab_control_center/backend/runtime/events.jsonl" \
  --trial-id "$trial_id" >"$trial_dir/logs/event_relay.log" 2>&1 &
relay_pid=$!
video_pid=""
if (( capture_video )); then
  curl -fsS --no-buffer "$CAMERA_URL" -o "$trial_dir/cobot_camera.mjpg" 2>"$trial_dir/logs/camera_capture.log" &
  video_pid=$!
fi

recorder_name="b002_recorder_${run}_$$"
ros2 bag record --all-topics --all-services --include-hidden-topics \
  --exclude-regex '^/oakd/(rgb|stereo|depth|left|right)(/.*)?$' \
  --storage mcap --storage-preset-profile zstd_fast --polling-interval 100 \
  --disable-keyboard-controls --node-name "$recorder_name" \
  --custom-data "trial_id=$trial_id" "condition=$condition" "can_color=$can_color" \
  -o "$trial_dir/rosbag" >"$trial_dir/logs/rosbag.log" 2>&1 &
bag_pid=$!

finished=0
finish() {
  (( finished )) && return
  finished=1
  echo "Finalizando gravação com flush seguro..."
  # Processos em background podem herdar SIGINT ignorado do shell. SIGTERM é
  # tratado pelo rosbag2 como encerramento gracioso e grava metadata/índice.
  kill -TERM "$bag_pid" 2>/dev/null || true
  wait "$bag_pid" 2>/dev/null || true
  kill -TERM "$sampler_pid" 2>/dev/null || true
  wait "$sampler_pid" 2>/dev/null || true
  kill -TERM "$relay_pid" 2>/dev/null || true
  wait "$relay_pid" 2>/dev/null || true
  if [[ -n "$video_pid" ]]; then kill -TERM "$video_pid" 2>/dev/null || true; wait "$video_pid" 2>/dev/null || true; fi
  for endpoint in cell/status turtlebot/status turtlebot/nav_readiness turtlebot/processes health/; do
    safe_name="${endpoint//\//_}"
    curl -fsS "$API_URL/api/v1/$endpoint" -o "$trial_dir/api_final/${safe_name}.json" || true
  done
  ros2 bag info "$trial_dir/rosbag" > "$trial_dir/rosbag_info.txt" 2>&1 || true
  if [[ -f "$trial_dir/log_offsets.tsv" ]]; then
    while IFS=$'\t' read -r log_source offset; do
      log_name="$(basename "$log_source")"
      dd if="$log_source" of="$trial_dir/logs/${log_name}.delta" bs=1 skip="$offset" status=none 2>/dev/null || true
    done < "$trial_dir/log_offsets.tsv"
  fi
  docker logs --since "$started_at_utc" future_lab_backend > "$trial_dir/logs/backend.delta.log" 2>&1 || true
  python3 "$PROJECT_ROOT/experiments/validate_trial.py" "$trial_dir" --mode "$mode" || true
  find "$trial_dir" -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > "$trial_dir/SHA256SUMS"
  echo "Dados encerrados em: $trial_dir"
}
trap finish INT TERM EXIT

sleep 3
kill -0 "$bag_pid" 2>/dev/null || { echo "ERRO: rosbag encerrou prematuramente; veja logs/rosbag.log"; exit 1; }
kill -0 "$relay_pid" 2>/dev/null || { echo "ERRO: relay de eventos encerrou; veja logs/event_relay.log"; exit 1; }
if (( capture_video )); then
  kill -0 "$video_pid" 2>/dev/null || { echo "ERRO: captura MJPEG encerrou; veja logs/camera_capture.log"; exit 1; }
fi
recorder_subscribed=0
for _ in $(seq 1 30); do
  if ros2 topic info /future_lab/events 2>/dev/null | grep -Eq 'Subscription count: [1-9][0-9]*'; then
    recorder_subscribed=1
    break
  fi
  sleep 1
done
(( recorder_subscribed == 1 )) || { echo "ERRO: rosbag não comprovou assinatura de /future_lab/events."; exit 1; }
echo "GRAVAÇÃO ATIVA: $trial_dir"
if [[ "$mode" == smoke ]]; then
  curl -fsS -X POST "$API_URL/api/v1/cell/integrated_real/preflight" -o "$trial_dir/smoke_preflight_response.json"
  sleep "$duration"
  finish
else
  echo "Agora execute o ciclo no dashboard. Pressione Ctrl+C somente após sucesso/falha e retorno seguro à dock."
  while kill -0 "$bag_pid" 2>/dev/null; do sleep 1; done
fi
