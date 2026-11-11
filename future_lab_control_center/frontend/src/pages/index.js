import React, { useState, useEffect } from 'react';
import NetworkStatusHeader from '../components/NetworkStatusHeader';
import CellControlPanel from '../components/CellControlPanel';
import CameraVisionPanel from '../components/CameraVisionPanel';
import TeachModePanel from '../components/TeachModePanel';
import TurtleBotDashboardTab from '../components/TurtleBotDashboardTab';
import NotificationToast from '../components/NotificationToast';
import PanicOverlayModal from '../components/PanicOverlayModal';
import RebootOverlayModal from '../components/RebootOverlayModal';
import InterruptOverlayModal from '../components/InterruptOverlayModal';
import { Bot, Cpu } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export default function Dashboard() {
  const { lang, t, tb } = useLanguage();
  const [activeTab, setActiveTab] = useState('cobot'); // 'cobot' | 'turtlebot'
  const [health, setHealth] = useState(null);
  const [cellStatus, setCellStatus] = useState(null);
  const [poses, setPoses] = useState(null);
  const [tbStatus, setTbStatus] = useState(null);
  const [tbNavReadiness, setTbNavReadiness] = useState(null);
  const [tbProcesses, setTbProcesses] = useState(null);
  const [notification, setNotification] = useState(null);
  const [isRebooting, setIsRebooting] = useState(false);

  // Estados Otimistas para Resposta Instantânea (0ms) nos Botões
  const [optimisticPump, setOptimisticPump] = useState(null);
  const [optimisticYoloTest, setOptimisticYoloTest] = useState(null);

  const getApiBase = () => {
    if (typeof window !== 'undefined') {
      const host = window.location.hostname || 'localhost';
      return `http://${host}:8000/api/v1`;
    }
    return 'http://localhost:8000/api/v1';
  };

  // Helper seguro para chamadas à API sem estourar erros de runtime unhandled
  const safeApiCall = async (url, options = {}, warningTitle = '⚠️ OPERATION WARNING') => {
    try {
      const res = await fetch(url, options);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = tb(data.detail || data.message) || `HTTP Error ${res.status}`;
        setNotification({
          type: 'warning',
          title: warningTitle,
          message: msg
        });
        return { ok: false, data };
      }
      return { ok: true, data };
    } catch (e) {
      console.warn("Erro na requisição API:", e);
      setNotification({
        type: 'error',
        title: t('connFailedTitle'),
        message: t('connFailedMsg')
      });
      return { ok: false, data: null };
    }
  };

  const refreshFastStatus = async () => {
    const apiBase = getApiBase();
    try {
      const [hRes, cRes, pRes, tbRes] = await Promise.all([
        fetch(`${apiBase}/health/`).catch(() => null),
        fetch(`${apiBase}/cell/status`).catch(() => null),
        fetch(`${apiBase}/cobot/poses`).catch(() => null),
        fetch(`${apiBase}/turtlebot/status`).catch(() => null),
      ]);

      if (hRes && hRes.ok) setHealth(await hRes.json());
      if (cRes && cRes.ok) {
        const cData = await cRes.json();
        setCellStatus(cData);
        setOptimisticPump(null);
        setOptimisticYoloTest(null);
      }
      if (pRes && pRes.ok) setPoses(await pRes.json());
      if (tbRes && tbRes.ok) setTbStatus(await tbRes.json());
    } catch (err) {
      console.error("Erro ao atualizar status rápido:", err);
    }
  };

  const refreshSlowStatus = async () => {
    const apiBase = getApiBase();
    try {
      const [navRes, procRes] = await Promise.all([
        fetch(`${apiBase}/turtlebot/nav_readiness`).catch(() => null),
        fetch(`${apiBase}/turtlebot/processes`).catch(() => null)
      ]);

      if (navRes && navRes.ok) setTbNavReadiness(await navRes.json());
      if (procRes && procRes.ok) setTbProcesses(await procRes.json());
    } catch (err) {
      console.error("Erro ao atualizar status lento:", err);
    }
  };

  // Atualização sob demanda depois de uma ação do operador.
  // refreshFastStatus e refreshSlowStatus são os dois laços de polling;
  // esta função dispara os dois de uma vez e é chamada no fim de cada handler.
  const refreshStatus = () => {
    refreshFastStatus();
    refreshSlowStatus();
  };

  useEffect(() => {
    refreshFastStatus();
    refreshSlowStatus();
    const intervalFast = setInterval(refreshFastStatus, 2000);
    const intervalSlow = setInterval(refreshSlowStatus, 10000);
    return () => {
      clearInterval(intervalFast);
      clearInterval(intervalSlow);
    };
  }, []);

  // Handlers Célula & Cobot
  const handleUpdateMode = async (payload) => {
    const apiBase = getApiBase();
    const modeObj = typeof payload === 'string' 
      ? { mode: payload, cooldown_sec: 5.0, yolo_conf: 0.60 } 
      : payload;
    await safeApiCall(`${apiBase}/cell/mode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(modeObj)
    }, t('modeConfigTitle'));
    refreshStatus();
  };

  const handleAutoStart = async () => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cell/auto/start`, { method: 'POST' });
    refreshStatus();
  };

  const handleAutoStop = async () => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cell/auto/stop`, { method: 'POST' });
    refreshStatus();
  };

  const handleStartIntegratedReal = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(
      `${apiBase}/cell/integrated_real/start`,
      { method: 'POST' },
      t('integratedRealTitle')
    );
    if (ok) {
      setNotification({
        type: 'success',
        title: t('integratedRealStartedTitle'),
        message: tb(data.message)
      });
    }
    refreshStatus();
  };

  const handleStopIntegratedReal = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(
      `${apiBase}/cell/integrated_real/stop`,
      { method: 'POST' },
      t('integratedRealStopTitle')
    );
    if (ok) {
      setNotification({
        type: 'warning',
        title: t('integratedRealStopTitle'),
        message: tb(data.message)
      });
    }
    refreshStatus();
  };

  const handleConfirmIntegratedDetection = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(
      `${apiBase}/cell/integrated_real/confirm_detection`,
      { method: 'POST' },
      t('integratedRealConfirmationTitle')
    );
    if (ok) {
      setNotification({
        type: 'warning',
        title: t('integratedRealConfirmationTitle'),
        message: tb(data.message)
      });
    }
    refreshStatus();
  };

  const handleManualStartScan = async () => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cell/manual/start_scan`, { method: 'POST' }, t('manualMoveScanTitle'));
    refreshStatus();
  };

  const handleManualAuthorizePick = async () => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cell/manual/authorize_pick`, { method: 'POST' });
    refreshStatus();
  };

  const handleManualAuthorizePlace = async () => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cell/manual/authorize_place`, { method: 'POST' });
    refreshStatus();
  };

  const handleInterrupt = async () => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cell/interrupt`, { method: 'POST' });
    refreshStatus();
  };

  const handleConfirmInterrupt = async (shouldAbort) => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cell/interrupt/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ abort: Boolean(shouldAbort) })
    }, t('cellInterruptTitle'));
    refreshStatus();
  };

  const handleEmergencyStop = async () => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cell/stop`, { method: 'POST' }, t('emergencyStopTitle'));
    refreshStatus();
  };

  const handlePanicStop = async () => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cell/panic`, { method: 'POST' });
    refreshStatus();
  };

  const handleResetPanic = async () => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cell/reset_panic`, { method: 'POST' });
    refreshStatus();
  };

  const handleRestartNanoHardware = async () => {
    setIsRebooting(true);
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/health/restart_nano_hardware`, { method: 'POST' }, t('restartingNanoTitleAlert'));
  };

  const handleTogglePump = async () => {
    const targetState = !Boolean(cellStatus?.pump_active);
    setOptimisticPump(targetState);
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cobot/pump`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ on: targetState })
    }, t('suctionPumpTitle'));
    refreshStatus();
  };

  const handleToggleYoloTest = async () => {
    const targetState = !Boolean(cellStatus?.yolo_test_active);
    setOptimisticYoloTest(targetState);
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cobot/yolo_test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: targetState, conf: cellStatus?.cell?.yolo_conf ?? 0.60 })
    });
    refreshStatus();
  };

  const handleRestartCamera = async () => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/health/restart_camera`, { method: 'POST' });
    refreshStatus();
  };

  const handleStopCamera = async () => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/health/stop_camera`, { method: 'POST' });
    refreshStatus();
  };

  const handleRelease = async (joint_id = null) => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cobot/teach/release`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ joint_id })
    });
    refreshStatus();
  };

  const handleLock = async () => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cobot/teach/lock`, { method: 'POST' });
    refreshStatus();
  };

  const handleRecord = async (name) => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/cobot/teach/record/${name}`, { method: 'POST' }, `${t('recordPoseTitle')} ${name ? name.toUpperCase() : ''}`);
    if (ok) {
      setNotification({
        type: 'success',
        title: `${t('poseRecordedTitle')} '${name ? name.toUpperCase() : ''}'`,
        message: t('poseRecordedMsg')
      });
    }
    refreshStatus();
  };

  const handleSave = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/cobot/teach/save`, { method: 'POST' }, t('saveCalibrationTitle'));
    if (ok) {
      setNotification({
        type: 'success',
        title: t('calibrationSavedTitle'),
        message: lang === 'en' ? t('calibrationSavedMsg') : (data.message || t('calibrationSavedMsg'))
      });
    }
    refreshStatus();
  };

  const handlePlayback = async (filename) => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cobot/teach/playback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename })
    });
    refreshStatus();
  };

  const handleClear = async () => {
    const apiBase = getApiBase();
    const { ok } = await safeApiCall(`${apiBase}/cobot/teach/clear`, { method: 'DELETE' });
    if (ok) {
      setNotification({
        type: 'warning',
        title: t('calibrationClearedTitle'),
        message: t('calibrationClearedMsg')
      });
    }
    await refreshStatus();
  };

  const handleRestore = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/cobot/teach/restore`, { method: 'POST' }, t('restoreBackupTitle'));
    if (ok) {
      setNotification({
        type: 'success',
        title: t('backupRestoredTitle'),
        message: lang === 'en' ? t('backupRestoredMsg') : (data?.message || t('backupRestoredMsg'))
      });
    }
    await refreshStatus();
  };

  const handleMovePose = async (name) => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cobot/move/${name}`, { method: 'POST' }, `${t('moveToPoseTitle')} ${name.toUpperCase()}`);
    refreshStatus();
  };

  const handleMovePoseFail = async (name) => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/cobot/move/${name}`, { method: 'POST' }, `${t('moveToPoseTitle')} ${name.toUpperCase()}`);
    refreshStatus();
  };

  const handleLaunchRviz = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/health/launch_rviz`, { method: 'POST' }, t('rviz3DTitle'));
    if (ok) {
      setNotification({
        type: 'info',
        title: t('rviz3DStartedTitle'),
        message: lang === 'en' ? t('rviz3DStartedMsg') : (data.message || t('rviz3DStartedMsg'))
      });
    }
  };

  // Handlers TurtleBot 4
  const handleTbDock = async () => {
    const apiBase = getApiBase();
    setNotification({
      type: 'info',
      title: t('tbSendingDockTitle'),
      message: t('tbSendingDockMsg')
    });
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/dock`, { method: 'POST' }, t('tbDockTitle'));
    if (ok) {
      setNotification({
        type: 'success',
        title: t('tbDockDoneTitle'),
        message: (lang === 'en' ? t('tbDockSentMsg') : (data.message || t('tbDockSentMsg')))
      });
    }
    refreshStatus();
  };

  const handleTbUndock = async () => {
    const apiBase = getApiBase();
    setNotification({
      type: 'info',
      title: t('tbSendingUndockTitle'),
      message: t('tbSendingUndockMsg')
    });
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/undock`, { method: 'POST' }, t('tbUndockTitle'));
    if (ok) {
      setNotification({
        type: 'success',
        title: t('tbUndockDoneTitle'),
        message: (lang === 'en' ? t('tbUndockSentMsg') : (data.message || t('tbUndockSentMsg')))
      });
    }
    refreshStatus();
  };

  const handleTbLaunchLocalization = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/launch_localization`, { method: 'POST' }, t('tbLocTitle'));
    if (ok) {
      setNotification({
        type: 'success',
        title: t('tbLocStartedTitle'),
        message: lang === 'en' ? t('tbLocStartedMsg') : (data.message || t('tbLocStartedMsg'))
      });
    }
    refreshStatus();
  };

  const handleTbLaunchNav2 = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/launch_nav2`, { method: 'POST' }, t('tbNav2Title'));
    if (ok) {
      setNotification({
        type: 'success',
        title: t('tbNav2StartedTitle'),
        message: lang === 'en' ? t('tbNav2StartedMsg') : (data.message || t('tbNav2StartedMsg'))
      });
    }
    refreshStatus();
  };

  const handleTbLaunchViz = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/launch_viz`, { method: 'POST' }, t('tbRvizNav2Title'));
    if (ok) {
      setNotification({
        type: 'success',
        title: t('tbRvizNav2StartedTitle'),
        message: lang === 'en' ? t('tbRvizNav2StartedMsg') : (data.message || t('tbRvizNav2StartedMsg'))
      });
    }
  };

  const handleTbRestartDaemon = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/restart_daemon`, { method: 'POST' }, t('tbRestartDaemonTitle'));
    if (ok) {
      setNotification({
        type: 'success',
        title: t('tbRestartDaemonStartedTitle'),
        message: lang === 'en' ? t('tbRestartDaemonStartedMsg') : (data.message || t('tbRestartDaemonStartedMsg'))
      });
    }
    refreshStatus();
  };

  const handleTbStopLocalization = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/stop_localization`, { method: 'POST' }, t('tbStopLocTitle'));
    if (ok) {
      setNotification({
        type: 'info',
        title: t('tbStopLocStartedTitle'),
        message: lang === 'en' ? t('tbStopLocStartedMsg') : (data.message || t('tbStopLocStartedMsg'))
      });
    }
    refreshStatus();
  };

  const handleTbStopNav2 = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/stop_nav2`, { method: 'POST' }, t('tbStopNav2Title'));
    if (ok) {
      setNotification({
        type: 'info',
        title: t('tbStopNav2StartedTitle'),
        message: lang === 'en' ? t('tbStopNav2StartedMsg') : (data.message || t('tbStopNav2StartedMsg'))
      });
    }
    refreshStatus();
  };

  const handleTbStopViz = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/stop_viz`, { method: 'POST' }, t('tbStopRvizTitle'));
    if (ok) {
      setNotification({
        type: 'info',
        title: t('tbStopRvizStartedTitle'),
        message: lang === 'en' ? t('tbStopRvizStartedMsg') : (data.message || t('tbStopRvizStartedMsg'))
      });
    }
    refreshStatus();
  };

  const handleTbStopMissionManagerProcess = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/stop_mission_manager_process`, { method: 'POST' }, t('tbStopMMTitle'));
    if (ok) {
      setNotification({
        type: 'info',
        title: t('tbStopMMStartedTitle'),
        message: lang === 'en' ? t('tbStopMMStartedMsg') : (data.message || t('tbStopMMStartedMsg'))
      });
    }
    refreshStatus();
  };

  const handleTbLaunchMissionManager = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/launch_mission_manager`, { method: 'POST' }, t('tbMMTitle'));
    if (ok) {
      setNotification({
        type: 'success',
        title: t('tbMMStartedTitle'),
        message: lang === 'en' ? t('tbMMStartedMsg') : (data.message || t('tbMMStartedMsg'))
      });
    }
    refreshStatus();
  };

  const handleTbMissionTestStartDelivery = async (item) => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/mission_test/start_delivery`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item })
    }, t('tbMissionSignalTitle'));
    if (ok) {
      setNotification({
        type: 'success',
        title: t('tbDeliveryStartedTitle'),
        message: tb(data.message)
      });
    }
    refreshStatus();
    return ok;
  };

  const handleTbMissionTestItemReleased = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/mission_test/item_released`, {
      method: 'POST'
    }, t('tbMissionSignalTitle'));
    if (ok) {
      setNotification({
        type: 'info',
        title: t('tbMissionSignalPublishedTitle'),
        message: tb(data.message)
      });
    }
    refreshStatus();
    return ok;
  };

  const handleTbTriggerRestock = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/trigger_restock`, { method: 'POST' }, t('tbRestockTitle'));
    if (ok) {
      setNotification({
        type: 'success',
        title: t('tbRestockStartedTitle'),
        message: lang === 'en' ? t('tbRestockStartedMsg') : (data.message || t('tbRestockStartedMsg'))
      });
    }
    refreshStatus();
  };

  const [tbDiag, setTbDiag] = useState(null);

  const handleTbTriggerFailure = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/trigger_failure`, { method: 'POST' }, t('tbFailureTitle'));
    if (ok) {
      setNotification({
        type: 'success',
        title: t('tbFailureStartedTitle'),
        message: lang === 'en' ? t('tbFailureStartedMsg') : (data.message || t('tbFailureStartedMsg'))
      });
    }
    refreshStatus();
  };

  const handleTbStopMission = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/stop_mission`, { method: 'POST' }, t('tbCancelMissionTitle'));
    if (ok) {
      const isPartial = data?.status === 'partial' || data?.nav_goal_cancelada === false;
      const firstAviso = (data?.avisos && data.avisos.length > 0) ? data.avisos[0] : '';
      setNotification({
        type: isPartial ? 'error' : 'warning',
        title: isPartial ? t('tbCancelUnconfirmedTitle') : t('tbCancelMissionStartedTitle'),
        message: isPartial ? (tb(data?.message || firstAviso) || t('tbCancelUnconfirmedMsg')) : (lang === 'en' ? t('tbCancelMissionStartedMsg') : (data?.message || t('tbCancelMissionStartedMsg')))
      });
    }
    refreshStatus();
  };

  const handleTbDiagnose = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/diagnose`, { method: 'GET' }, t('tbDiagnoseTitle'));
    if (ok) {
      setTbDiag(data);
      const statusText = data.ping_ok ? (lang === 'pt' ? 'ONLINE' : 'ONLINE') : (lang === 'pt' ? 'SEM PING' : 'NO PING');
      const topicsText = lang === 'pt' ? 'tópicos ROS 2 visíveis' : 'ROS 2 topics visible';
      setNotification({
        type: 'success',
        title: t('tbDiagnoseStartedTitle'),
        message: `IP 192.168.0.129: ${statusText}. ${data.topics_count} ${topicsText}!`
      });
    }
  };

  const handleTbTriggerPatrol = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/trigger_patrol`, { method: 'POST' }, t('tbPatrolTitle'));
    if (ok) {
      setNotification({
        type: 'success',
        title: t('tbPatrolStartedTitle'),
        message: lang === 'en' ? t('tbPatrolStartedMsg') : (data.message || t('tbPatrolStartedMsg'))
      });
    }
    refreshStatus();
  };

  const handleTbLaunchIntegrated3D = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/launch_integrated_3d`, { method: 'POST' }, t('tbViz3DTitle'));
    if (ok) {
      setNotification({
        type: 'success',
        title: t('tbViz3DStartedTitle'),
        message: lang === 'en' ? t('tbViz3DStartedMsg') : (data.message || t('tbViz3DStartedMsg'))
      });
    }
  };

  const handleTbTeleop = async (linear_x, angular_z) => {
    const apiBase = getApiBase();
    await safeApiCall(`${apiBase}/turtlebot/teleop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ linear_x, angular_z })
    });
  };

  const handleTbStartOakdCamera = async () => {
    const apiBase = getApiBase();
    const { ok, data } = await safeApiCall(`${apiBase}/turtlebot/start_oakd_camera`, { method: 'POST' }, t('tbOakdCameraTitle'));
    if (ok) {
      setNotification({
        type: 'success',
        title: t('tbOakdCameraStartedTitle'),
        message: lang === 'en' ? t('tbOakdCameraStartedMsg') : (data.message || t('tbOakdCameraStartedMsg'))
      });
    }
  };

  // Valores Finais (Considera o Estado Otimista Instantâneo se Presente)
  const currentPumpActive = optimisticPump !== null ? optimisticPump : Boolean(cellStatus?.pump_active);
  const currentYoloTestActive = optimisticYoloTest !== null ? optimisticYoloTest : Boolean(cellStatus?.yolo_test_active);

  return (
    <main className="min-h-screen p-4 md:p-8 max-w-7xl mx-auto space-y-6 relative">
      {/* Modal Popup de Reboot e Inicialização Centralizada */}
      <RebootOverlayModal
        isRebooting={isRebooting}
        onRebootComplete={() => {
          setIsRebooting(false);
          refreshStatus();
        }}
      />

      {/* Modal Popup de Bloqueio de Pânico Absoluto */}
      <PanicOverlayModal
        isLocked={Boolean(cellStatus?.cell?.panic_locked)}
        onResetPanic={handleResetPanic}
      />

      {/* Modal Popup de Confirmação de Interrupção (SIM, ABORTAR / NÃO, CONTINUAR) */}
      <InterruptOverlayModal
        isInterrupted={cellStatus?.cell?.status === 'interrupted_paused'}
        onConfirmInterrupt={handleConfirmInterrupt}
      />

      {/* Toast de Notificação Dinâmica */}
      <NotificationToast
        notification={notification}
        onClose={() => setNotification(null)}
      />

      {/* Topbar de Conectividade de Rede */}
      <NetworkStatusHeader healthData={health} />

      {/* Barra de Navegação por Abas (Tab Bar Switcher) */}
      <div className="flex items-center gap-3 p-1.5 bg-slate-900/80 rounded-2xl border border-slate-700/60 backdrop-blur-md">
        <button
          onClick={() => setActiveTab('cobot')}
          className={`flex-1 py-3 px-5 rounded-xl font-extrabold text-sm flex items-center justify-center gap-2.5 transition-all ${
            activeTab === 'cobot'
              ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/20 border border-blue-400/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Cpu className="w-5 h-5" />
          <span>🦾 {t('tabCellControl')}</span>
        </button>

        <button
          onClick={() => setActiveTab('turtlebot')}
          className={`flex-1 py-3 px-5 rounded-xl font-extrabold text-sm flex items-center justify-center gap-2.5 transition-all ${
            activeTab === 'turtlebot'
              ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg shadow-purple-500/20 border border-purple-400/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Bot className="w-5 h-5" />
          <span>{t('tabTurtleBotControl')}</span>
        </button>
      </div>

      {/* Conteúdo da Aba 1: Célula Robótica */}
      <div className={activeTab === 'cobot' ? 'space-y-6 block' : 'hidden'}>
        <CellControlPanel
          cellState={cellStatus?.cell}
          tbNavReadiness={tbNavReadiness}
          tbProcesses={tbProcesses}
          tbStatus={tbStatus}
          onUpdateMode={handleUpdateMode}
          onAutoStart={handleAutoStart}
          onAutoStop={handleAutoStop}
          onStartIntegratedReal={handleStartIntegratedReal}
          onStopIntegratedReal={handleStopIntegratedReal}
          onConfirmIntegratedDetection={handleConfirmIntegratedDetection}
          onManualStartScan={handleManualStartScan}
          onManualAuthorizePick={handleManualAuthorizePick}
          onManualAuthorizePlace={handleManualAuthorizePlace}
          onInterrupt={handleInterrupt}
          onConfirmInterrupt={handleConfirmInterrupt}
          onEmergencyStop={handleEmergencyStop}
          onPanicStop={handlePanicStop}
          onRestartNanoHardware={handleRestartNanoHardware}
          onTestHandshake={async (itemClass) => {
            const apiBase = getApiBase();
            const { ok, data } = await safeApiCall(`${apiBase}/cell/test_handshake`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ item_class: itemClass })
            }, t('tbHandshakeTestTitle'));
            if (ok) {
              setNotification({
                type: 'success',
                title: t('tbHandshakeTestStartedTitle'),
                message: lang === 'en' ? t('tbHandshakeTestStartedMsg') : (data.message || t('tbHandshakeTestStartedMsg'))
              });
            }
            refreshStatus();
          }}
        />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <CameraVisionPanel
            streamUrl={health?.devices?.jetson_nano?.camera_stream_url}
            cameraOnline={Boolean(health?.devices?.jetson_nano?.camera_stream_online)}
            lastYolo={cellStatus?.last_yolo}
            yoloConfThreshold={cellStatus?.cell?.yolo_conf ?? 0.60}
            pumpActive={currentPumpActive}
            yoloTestActive={currentYoloTestActive}
            onTogglePump={handleTogglePump}
            onToggleYoloTest={handleToggleYoloTest}
            onRestartCamera={handleRestartCamera}
            onStopCamera={handleStopCamera}
          />

          <TeachModePanel
            cellState={cellStatus?.cell}
            posesData={poses}
            onRelease={handleRelease}
            onLock={handleLock}
            onRecord={handleRecord}
            onSave={handleSave}
            onPlayback={handlePlayback}
            onClear={handleClear}
            onRestore={handleRestore}
            onMovePose={handleMovePose}
            onMovePoseFail={handleMovePoseFail}
            onLaunchRviz={handleLaunchRviz}
          />
        </div>
      </div>

      {/* Conteúdo da Aba 2: TurtleBot 4 (AMR) */}
      <div className={activeTab === 'turtlebot' ? 'space-y-6 block' : 'hidden'}>
        <TurtleBotDashboardTab
          tbStatus={tbStatus}
          tbDiag={tbDiag}
          tbNavReadiness={tbNavReadiness}
          tbProcesses={tbProcesses}
          onDiagnose={handleTbDiagnose}
          onDock={handleTbDock}
          onUndock={handleTbUndock}
          onLaunchLocalization={handleTbLaunchLocalization}
          onLaunchNav2={handleTbLaunchNav2}
          onLaunchViz={handleTbLaunchViz}
          onLaunchMissionManager={handleTbLaunchMissionManager}
          onMissionTestStartDelivery={handleTbMissionTestStartDelivery}
          onMissionTestItemReleased={handleTbMissionTestItemReleased}
          onTriggerFailure={handleTbTriggerFailure}
          onTriggerRestock={handleTbTriggerRestock}
          onTriggerPatrol={handleTbTriggerPatrol}
          onStopMission={handleTbStopMission}
          onLaunchIntegrated3D={handleTbLaunchIntegrated3D}
          onTeleop={handleTbTeleop}
          onStartOakdCamera={handleTbStartOakdCamera}
          onRestartDaemon={handleTbRestartDaemon}
          onStopLocalization={handleTbStopLocalization}
          onStopNav2={handleTbStopNav2}
          onStopViz={handleTbStopViz}
          onStopMissionManagerProcess={handleTbStopMissionManagerProcess}
        />
      </div>
    </main>
  );
}
