import asyncio
import threading
import socket
from flask import Flask, render_template, jsonify, request
from mavsdk import System
from mavsdk.mission import MissionItem, MissionPlan
from mavsdk.action import ActionError

app = Flask(__name__)

# 전역 변수
mission_state = {
    "mode": "idle",
    "patrol_waypoints": [],
    "emergency_target": None,
    "status_message": "드론 연결 대기 중...",
    "is_flying": False
}
new_mission_event = asyncio.Event()
controller_loop = None 

# --- 드론 제어 로직 (비동기) ---
async def drone_controller():
    global mission_state, controller_loop
    
    controller_loop = asyncio.get_running_loop()
    
    drone = System()
    await drone.connect(system_address="udp://:14540")

    async for state in drone.telemetry.health():
        if state.is_global_position_ok and state.is_home_position_ok:
            print("[Controller] 드론 상태 양호. 사전 비행 점검 완료.")
            mission_state["status_message"] = "대기 중..."
            break

    while True:
        await new_mission_event.wait()
        new_mission_event.clear()

        if not mission_state["mode"] in ["patrol", "emergency"]:
            continue
        
        mission_state["is_flying"] = True
        mission_items = []
        mode = mission_state["mode"]

        # <<< 여기가 수정된 부분입니다 (빠진 인자 3개 추가)
        if mode == "patrol":
            mission_state["status_message"] = f"{len(mission_state['patrol_waypoints'])}개 지점 정찰 중..."
            mission_items = [
                MissionItem(wp['lat'], wp['lon'], 20, 10, True, 
                            float('nan'), float('nan'), MissionItem.CameraAction.NONE, 
                            float('nan'), float('nan'), float('nan'), float('nan'), float('nan'),
                            MissionItem.VehicleAction.NONE) # 14번째 인자 추가
                for wp in mission_state["patrol_waypoints"]
            ]
        elif mode == "emergency":
            target = mission_state["emergency_target"]
            mission_state["status_message"] = f"긴급 출동: {target['lat']:.5f}, {target['lon']:.5f}"
            mission_items.append(
                MissionItem(target['lat'], target['lon'], 20, 15, True, 
                            float('nan'), float('nan'), MissionItem.CameraAction.NONE, 
                            float('nan'), float('nan'), float('nan'), float('nan'), float('nan'),
                            MissionItem.VehicleAction.NONE) # 14번째 인자 추가
            )
        # --- 여기까지 수정 ---
        
        try:
            if mode == "emergency":
                try:
                    await drone.mission.pause_mission()
                    await asyncio.sleep(1)
                    await drone.mission.clear_mission()
                except Exception: pass
            
            mission_plan = MissionPlan(mission_items)
            await drone.mission.set_return_to_launch_after_mission(True)
            await drone.mission.upload_mission(mission_plan)
            
            await drone.action.arm()
            
            mission_state["status_message"] = "이륙 중..."
            await drone.action.set_takeoff_altitude(20)
            await drone.action.takeoff()
            await asyncio.sleep(5)

            mission_state["status_message"] = "임무 수행 중..."
            await drone.mission.start_mission()

            async for mission_progress in drone.mission.mission_progress():
                if mission_state["mode"] != mode: break
                if mission_progress.current == mission_progress.total: break
        except Exception as e:
            print(f"[Controller] 드론 비행 중 오류 발생: {e}")
            mission_state["status_message"] = f"오류: {e}"
        finally:
            mission_state["is_flying"] = False
            if mission_state["mode"] == mode:
                 mission_state["mode"] = "idle"
                 mission_state["status_message"] = "대기 중..."

# --- UDP 및 Flask 라우트 (이전과 동일, 변경 없음) ---
def udp_emergency_listener():
    global mission_state
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', 5005))
    while True:
        data, addr = sock.recvfrom(1024)
        try:
            lat_str, lon_str = data.decode('utf-8').strip().split(',')
            lat, lon = float(lat_str), float(lon_str)
            mission_state["emergency_target"] = {"lat": lat, "lon": lon}
            mission_state["mode"] = "emergency_alert"
            mission_state["status_message"] = "!!! 긴급 출동 요청 수신 !!!"
        except Exception: pass
@app.route('/')
def index(): return render_template('index.html')
@app.route('/status')
def status(): return jsonify(mission_state)
@app.route('/set_patrol_waypoints', methods=['POST'])
def set_patrol_waypoints():
    if not mission_state["is_flying"]:
        waypoints = request.json.get('waypoints', [])
        mission_state["patrol_waypoints"] = waypoints
        return jsonify({"result": "success", "message": f"{len(waypoints)}개의 정찰 지점 설정 완료."})
    return jsonify({"result": "error", "message": "드론이 비행 중에는 경로를 변경할 수 없습니다."})
def trigger_event():
    new_mission_event.set()
@app.route('/start_patrol', methods=['POST'])
def start_patrol():
    if not mission_state["is_flying"] and mission_state["patrol_waypoints"]:
        mission_state["mode"] = "patrol"
        if controller_loop: controller_loop.call_soon_threadsafe(trigger_event)
        return jsonify({"result": "success", "message": "정찰 임무를 시작합니다."})
    return jsonify({"result": "error", "message": "비행 중이거나 설정된 경로가 없습니다."})
@app.route('/dispatch_emergency', methods=['POST'])
def dispatch_emergency():
    if mission_state["mode"] == "emergency_alert":
        mission_state["mode"] = "emergency"
        if controller_loop: controller_loop.call_soon_threadsafe(trigger_event)
        return jsonify({"result": "success", "message": "긴급 출동 명령을 전송했습니다."})
    return jsonify({"result": "error", "message": "긴급 출동을 할 수 없는 상태입니다."})
@app.route('/cancel_alert', methods=['POST'])
def cancel_alert():
    if mission_state["mode"] == "emergency_alert":
        mission_state["mode"] = "idle"
        mission_state["emergency_target"] = None
        mission_state["status_message"] = "대기 중..."
        return jsonify({"result": "success"})
    return jsonify({"result": "error"})
if __name__ == '__main__':
    threading.Thread(target=lambda: asyncio.run(drone_controller()), daemon=True).start()
    threading.Thread(target=udp_emergency_listener, daemon=True).start()
    app.run(host='0.0.0.0', port=1717)
