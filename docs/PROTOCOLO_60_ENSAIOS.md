# Protocolo de aquisição — 60 ciclos Cobot + TurtleBot 4

## Objetivo e limites

Este protocolo grava um ciclo físico completo desde o comando no dashboard até o retorno do TurtleBot à dock. A câmera do Cobot continua visível no painel web. O modo integrado executa o YOLO sem abrir janelas OpenCV; a OAK-D do TurtleBot não é ligada automaticamente. O gravador pode salvar o MJPEG bruto do Cobot, sem renderização ou recodificação, para reduzir CPU.

Um ensaio real somente é válido com uma lata física e inspeção de segurança. O teste `--smoke` valida a infraestrutura de aquisição sem mover os robôs.

## O que fica registrado

- rosbag MCAP comprimido com todos os tópicos descobertos, tópicos ocultos de actions e eventos de serviços, exceto imagens brutas OAK-D;
- `/future_lab/events`, com cada POST/PUT/PATCH/DELETE do dashboard e as transições do modo integrado/handshake;
- `/odom`, `/tf`, `/amcl_pose`, `/plan`, comandos de velocidade, laser, bateria e dock do TurtleBot;
- `/joint_states`, `/joint_states_raw`, comandos e actions do Cobot;
- classe YOLO, chegada ao pickup e liberação da lata;
- estado das APIs a 1 Hz, antes e depois do ciclo;
- inventário inicial de nós/tópicos, versão Git, condição, operador e observações;
- stream MJPEG bruto do Cobot (padrão; use `--no-video` somente se a carga precisar ser isolada). Imagens OAK-D são excluídas porque ativá-las por assinatura acrescentou centenas de MB em poucos minutos e altera a carga do PC; laser, odometria e navegação continuam gravados;
- checksums e validação automática final.

Os bags grandes ficam fora do repositório em `/home/future-lab/B002_experiment_data`. O JSONL do backend em `future_lab_control_center/backend/runtime/events.jsonl` é apenas contingência e está ignorado pelo Git.

Durante a aquisição, `event_relay.py` acompanha esse JSONL a partir do início do ensaio e o replica em `/future_lab/events`. Assim, a gravação dos cliques não depende da thread ROS interna do backend; `event_id` permite remover duplicatas caso as duas vias entreguem o mesmo evento.

## Desenho experimental

São 20 repetições por condição: `no_obstacle`, `static_obstacle` e `dynamic_obstacle`. Não faça primeiro todas as 20 de uma condição: isso confundiria a condição com bateria, aquecimento e horário. Gere uma ordem balanceada e reproduzível:

```bash
cd /home/future-lab/B002_Future_Lab_Bots
mkdir -p /home/future-lab/B002_experiment_data/campaign_01
./experiments/generate_campaign_plan.py \
  --seed 20260815 \
  --output /home/future-lab/B002_experiment_data/campaign_01/campaign_plan.csv
```

Defina antes do primeiro ensaio:

- sem obstáculo: corredor integralmente livre;
- estático: o mesmo objeto, posição e orientação marcados no piso e fotografados;
- dinâmico: uma pessoa treinada cruza a mesma linha, no mesmo sentido e faixa de velocidade, sem entrar na distância mínima de segurança;
- cores: 10 azuis e 10 vermelhas por condição, já balanceadas no CSV;
- ensaio inválido não substitui silenciosamente o original: marque `invalid`, descreva a causa e grave uma repetição adicional com novo identificador.

Para pessoas e vídeo, obtenha consentimento e aplique a política de privacidade do laboratório.

## Preparação única

No diretório do projeto:

```bash
cd /home/future-lab/B002_Future_Lab_Bots
chmod +x experiments/record_trial.sh experiments/*.py
./future_lab_control_center/START_LAB.sh
```

No dashboard em `http://localhost:3000`, confirme que a câmera MJPEG do Cobot aparece no painel. Não ligue a OAK-D só para gravar dados: o laser e a odometria são independentes e o custo computacional da câmera pode alterar o experimento.

Antes da campanha, valide o gravador sem movimento:

```bash
./experiments/record_trial.sh --smoke --duration 10 --campaign campaign_01
```

O portão passa somente se `validation.json` mostrar `"valid": true`, `/future_lab/events` tiver mensagens e o comando de preflight aparecer no bag. O preflight não envia comando de movimento.

## Preparação diária do sistema

1. Remova pessoas e objetos da área móvel; deixe o botão de emergência acessível e um observador dedicado.
2. Posicione a lata na zona marcada, mas fora do campo durante a etapa que exige câmera vazia.
3. Ligue Nano/Cobot, TurtleBot e PC. Inicie com `START_LAB.sh`.
4. No dashboard, confirme: Cobot real conectado, bomba desligada, TurtleBot dockado, telemetria fresca, `mission_ready` verde, câmera do Cobot online e nenhum workflow ativo.
5. Abra RViz/MoveIt apenas pelos controles previstos no modo integrado. Não abra janelas OpenCV paralelas.
6. Se qualquer medição estiver ausente, não force o ensaio. Corrija a origem e repita o smoke.

## Execução de cada ensaio

Leia a próxima linha `pending` do CSV. Em um terminal, inicie a aquisição **antes** de clicar no dashboard. Exemplo:

```bash
cd /home/future-lab/B002_Future_Lab_Bots
./experiments/record_trial.sh \
  --campaign campaign_01 \
  --condition static_obstacle \
  --run 7 \
  --can blue \
  --operator "nome" \
  --notes "obstaculo na marca S1"
```

O script só anuncia `GRAVAÇÃO ATIVA` depois destes portões:

1. backend e APIs respondem;
2. telemetria do TurtleBot é fresca e ele está dockado;
3. `mission_ready == true`;
4. nenhum handshake/modo integrado está ativo;
5. `/dock_status` e `/joint_states` são visíveis no DDS; `/future_lab/events` comprova uma assinatura antes de liberar o ensaio. Na dock, `/odom`, `/scan` e TF dinâmica podem dormir e só são exigidos no bag real depois do undock;
6. há pelo menos 10 GiB livres;
7. o processo rosbag permaneceu vivo por três segundos.

Depois de `GRAVAÇÃO ATIVA`:

1. Selecione a aba **Célula Robótica (MyCobot 280 & Visão)**.
2. Confira a imagem ao vivo e clique no botão principal de **Operação Integrada Real — YOLO + Cobot + TurtleBot**.
3. Aguarde o braço chegar à pose de scan e o painel pedir campo limpo. Não apresente a lata antes dessa confirmação.
4. Quando o painel indicar espera do YOLO real, apresente a lata na marca definida, sem entregar manualmente ao braço.
5. Só confirme a detecção se classe, cor e confiança exibidas corresponderem à lata real.
6. Afaste-se. O Cobot deve executar pick/place; o TurtleBot deve undock, confirmar pickup, receber a liberação, entregar no destino da cor e retornar à dock.
7. Não pressione `Ctrl+C` enquanto houver movimento. Ao final, confirme no painel sucesso ou falha, TurtleBot dockado e bomba desligada.
8. Pressione `Ctrl+C` no terminal. Aguarde `Dados encerrados em:` e leia `validation.json`.
9. Atualize a linha do CSV para `valid`, `failed` ou `invalid`, sempre preenchendo a causa quando não for válida.

## Portões de validade de um ciclo real

O arquivo `validation.json` precisa indicar:

- duração mínima de 30 s;
- ao menos uma mensagem em `/future_lab/events`, `/odom`, `/tf`, `/joint_states`, `/dock_status`, `/scan`, `/battery_state`, `/product_class`, `/turtlebot_at_pickup`, `/item_released_on_tb4` e `/amcl_pose`;
- `dashboard_state.jsonl` presente.

Além da validação automática, confira no estado final:

- `handshake.success == true` e modo integrado concluído;
- TurtleBot `is_docked == true` e telemetria fresca;
- bomba do Cobot desligada e braço em HOME medido;
- nenhum processo duplicado (`bt_navigator` nunca pode ter contagem maior que 1);
- não houve parada do gravador antes do fim.

Essas verificações não devem ser substituídas pela mensagem “sucesso” do software.

## Parada, falha e recuperação

Em risco físico, use primeiro o mecanismo de emergência apropriado; preservar dados é secundário. Depois de estabilizar os robôs, pressione `Ctrl+C`: o script envia SIGTERM gracioso ao rosbag para gravar índice/metadata antes de encerrar os auxiliares.

Se o workflow falhar sem risco, aguarde o rollback terminar e confirme dock/bomba/HOME antes de encerrar. Nunca inicie outra missão em cima de uma ativa. Se o terminal morrer, procure o gravador com `pgrep -af ros2.*bag.*record`, finalize com `kill -TERM PID` e só então valide o diretório.

Erros comuns:

- tópico mínimo ausente: não altere a lista; confirme Discovery Server e que `FASTDDS_BUILTIN_TRANSPORTS`/`ROS_AUTOMATIC_DISCOVERY_RANGE` não limitaram o grafo;
- bag sem metadata: encerramento abrupto; ensaio inválido;
- `/future_lab/events` sem mensagens: backend antigo ou não reiniciado;
- câmera bruta aumenta carga: compare um smoke com e sem `--no-video`; documente e mantenha a mesma política nos 60 ensaios;
- disco baixo: mova a campanha concluída e valide checksums, sem apagar a única cópia.

## Inspeção e replay

```bash
TRIAL=/home/future-lab/B002_experiment_data/campaign_01/trials/SEU_TRIAL
source /opt/ros/jazzy/setup.bash
ros2 bag info "$TRIAL/rosbag"
less "$TRIAL/rosbag_info.txt"
jq . "$TRIAL/validation.json"
```

Faça replay apenas com os robôs/processos de controle físico isolados. Um bag contém tópicos de comando e eventos de serviços; reproduzir tudo no grafo físico ativo é perigoso. Para análise segura, use outro `ROS_DOMAIN_ID` ou ambiente offline:

```bash
export ROS_DOMAIN_ID=77
ros2 bag play "$TRIAL/rosbag" --clock
```

Configure RViz com `use_sim_time=true` no domínio isolado. O arquivo `cobot_camera.mjpg` é a captura bruta multipart; mantenha-o associado ao `trial.json` e aos checksums.

## Métricas sugeridas

Calcule por condição: taxa de conclusão, tempo total, tempo YOLO→pickup, pickup→release, release→delivery, tempo de docking, comprimento do caminho por `/odom`, número de replans por `/plan`, paradas/comandos de velocidade, erro final de juntas e bateria inicial/final. Para distância mínima de obstáculo, derive de `/scan` com a pose/TF correspondente; não use apenas o menor range bruto sem filtrar geometria e validade.
