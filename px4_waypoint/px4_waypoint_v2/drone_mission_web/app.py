import asyncio
import threading
import socket
import math
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

# --- 헬퍼 함수 ---
def get_distance_metres(aLocation1, aLocation2):
    """두 위도/경도 지점 사이의 거리를 미터 단위로 반환"""
    dlat = aLocation2.latitude_deg - aLocation1.latitude_deg
    dlong = aLocation2.longitude_deg - aLocation1.longitude_deg
    return math.sqrt((dlat*dlat) + (dlong*dlong)) * 1.113195e5

# --- 메인 드론 제어 로직 (비동기) ---
async def drone_controller():
    global mission_state
    
    drone = System()
    await drone.connect(system_address="udp://:14540")

    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("[Controller] 드론 상태 양호.")
            mission_state["status_message"] = "대기 중..."
            break

    while True:
        await asyncio.sleep(1)

        mode_to_run = None
        if mission_state["mode"] == "patrol_pending":
            mode_to_run = "patrol"
        elif mission_state["mode"] == "emergency_pending":
            mode_to_run = "emergency"
        
        if not mode_to_run:
            continue
        
        try:
            # <<< 여기가 핵심 로직입니다 >>>
            if mode_to_run == "emergency":
                # 1. 긴급 출동 모드: goto_location 사용
                mission_state["mode"] = "emergency"
                target = mission_state["emergency_target"]
                lat, lon = target['lat'], target['lon']
                mission_state["status_message"] = f"긴급 출동: {lat:.5f}, {lon:.5f}"
                print(f"[Controller] 긴급 출동 명령 수신! 목표: {lat}, {lon}")

                # 현재 임무를 잠시 멈추고 goto 명령 실행
                await drone.mission.pause_mission()
                await drone.action.goto_location(lat, lon, 20, 0)
                mission_state["is_flying"] = True

                # 목표 지점에 도착할 때까지 대기
                async for position in drone.telemetry.position():
                    target_pos = type('obj', (object,), {'latitude_deg' : lat, 'longitude_deg' : lon})
                    distance = get_distance_metres(position, target_pos)
                    print(f"[Controller] 목표까지 남은 거리: {distance:.2f} m")
                    if distance < 2.0: # 2미터 이내로 가까워지면 도착으로 간주
                        print("[Controller] 긴급 목표 지점 도착.")
                        break
                
                await asyncio.sleep(5) # 목표 지점에서 5초간 대기
                print("[Controller] 임무 완료. 기지로 복귀합니다.")
                await drone.action.return_to_launch()

            elif mode_to_run == "patrol":
                # 2. 정찰 모드: Mission 사용 (기존과 유사)
                if not mission_state["patrol_waypoints"]: continue
                mission_state["mode"] = "patrol"
                mission_state["status_message"] = "정찰 임무 시작 중..."
                mission_items = [MissionItem(wp['lat'], wp['lon'], 20, 10, True, float('nan'), float('nan'), MissionItem.CameraAction.NONE, float('nan'), float('nan'), float('nan'), float('nan'), float('nan'), MissionItem.VehicleAction.NONE) for wp in mission_state["patrol_waypoints"]]
                mission_plan = MissionPlan(mission_items)
                await drone.mission.set_return_to_launch_after_mission(True)
                await drone.mission.upload_mission(mission_plan)

                if not mission_state["is_flying"]:
                    await drone.action.arm()
                    await drone.action.set_takeoff_altitude(20)
                    await drone.action.takeoff()
                    mission_state["is_flying"] = True

                await drone.mission.start_mission()
                mission_state["status_message"] = "임무 수행 중..."
                
                # 정찰 중 긴급 신호가 오면 중단되도록 감시
                async for mission_progress in drone.mission.mission_progress():
                    if mission_state["mode"] == "emergency_pending":
                        print("[Controller] 정찰 중 긴급 신호 감지! 정찰을 중단합니다.")
                        break # 현재 미션 루프를 탈출하여 다음 루프에서 긴급 출동 처리
                    if mission_progress.current == mission_progress.total:
                        break

        except Exception as e:
            print(f"[Controller] 비행 중 오류: {e}")
        finally:
            # 미션이 끝나면 항상 상태를 초기화
            mission_state["is_flying"] = False
            mission_state["mode"] = "idle"
            mission_state["status_message"] = "대기 중..."

# --- UDP 및 Flask 라우트 (변경 없음) ---
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
        mission_state["patrol_waypoints"] = request.json.get('waypoints', [])
        return jsonify({"result": "success"})
    return jsonify({"result": "error"})
@app.route('/start_patrol', methods=['POST'])
def start_patrol():
    if not mission_state["is_flying"] and mission_state["patrol_waypoints"]:
        mission_state["mode"] = "patrol_pending"
        return jsonify({"result": "success"})
    return jsonify({"result": "error"})
@app.route('/dispatch_emergency', methods=['POST'])
def dispatch_emergency():
    if mission_state["mode"] in ["emergency_alert", "patrol"]:
        mission_state["mode"] = "emergency_pending"
        return jsonify({"result": "success"})
    return jsonify({"result": "error"})
@app.route('/cancel_alert', methods=['POST'])
def cancel_alert():
    current_mode = "idle"
    if mission_state["is_flying"]:
        current_mode = "patrol"
    mission_state["mode"] = current_mode
    return jsonify({"result": "success"})
if __name__ == '__main__':
    threading.Thread(target=lambda: asyncio.run(drone_controller()), daemon=True).start()
    threading.Thread(target=udp_emergency_listener, daemon=True).start()
    app.run(host='0.0.0.0', port=1717)
