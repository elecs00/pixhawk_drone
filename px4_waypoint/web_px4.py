#!/usr/bin/env python3
import asyncio
from aiohttp import web
from mavsdk import System
from mavsdk.mission import MissionItem, MissionPlan, MissionError
import socket

coordinate_queue = asyncio.Queue()
pending_coordinate = None
response_event = asyncio.Event()

# UDP 좌표 수신 백그라운드 태스크
async def coordinate_listener():
    global pending_coordinate
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', 5005))
    print("🟢 안드로이드 앱으로부터 좌표 수신 대기 중...")

    loop = asyncio.get_event_loop()
    while True:
        data, addr = await loop.run_in_executor(None, sock.recvfrom, 1024)
        received_data = data.decode('utf-8').strip()
        print(f"✅ 좌표 수신 완료: {received_data}")

        try:
            lat_str, lon_str = received_data.split(',')
            latitude = float(lat_str)
            longitude = float(lon_str)
        except (ValueError, IndexError) as e:
            print(f"❌ 수신된 좌표 데이터 파싱 오류: {e}")
            continue

        pending_coordinate = (latitude, longitude)
        response_event.clear()
        print(f"📍 새 미션 위도: {latitude}, 경도: {longitude}")
        print("웹페이지에서 수락 여부를 기다립니다...")

        # 수락 여부가 결정될 때까지 대기
        await response_event.wait()

# 웹페이지 핸들러 (좌표 및 수락 폼 제공)
async def index(request):
    if pending_coordinate is None:
        html = """
        <html><body>
            <h2>현재 대기 중인 미션 좌표가 없습니다.</h2>
            <p>안드로이드 앱에서 좌표를 보내면 이 곳에 미션 수락 여부가 표시됩니다.</p>
        </body></html>
        """
        return web.Response(content_type='text/html', text=html)

    lat, lon = pending_coordinate
    html = f"""
    <html><body>
        <h2>새로운 미션 좌표 수신</h2>
        <p>위도: {lat}<br>경도: {lon}</p>
        <form action="/respond" method="post">
            <button name="choice" value="yes" type="submit">YES</button>
            <button name="choice" value="no" type="submit">NO</button>
        </form>
    </body></html>
    """
    return web.Response(content_type='text/html', text=html)

# 수락/거절 POST 수신 처리
async def respond(request):
    global pending_coordinate
    data = await request.post()
    choice = data.get('choice')
    if choice == 'yes' and pending_coordinate is not None:
        print("사용자가 미션을 수락했습니다.")
        await coordinate_queue.put(pending_coordinate)
    else:
        print("사용자가 미션을 거절했습니다.")
    pending_coordinate = None
    response_event.set()
    return web.Response(text="응답이 처리되었습니다. 이 창을 닫으셔도 됩니다.")

# 드론 미션 매니저 태스크 (미션 실행)
async def run_mission_manager():
    drone = System()
    await drone.connect(system_address="udp://:14540")
    print("🚁 드론 연결 대기 중...")

    async for state in drone.telemetry.health():
        if state.is_global_position_ok and state.is_home_position_ok:
            print("✅ 드론 GPS 및 Home 위치 확인 완료.")
            break

    print("드론 최초 시동(Arming)...")
    await drone.action.arm()

    while True:
        latitude, longitude = await coordinate_queue.get()
        print("\n⚡️ 새로운 미션 요청 수신! 미션 중단 및 새 미션 설정 중...")

        try:
            try:
                await drone.mission.pause_mission()
                print("⏸️ 현재 미션 일시 중지 완료.")
            except MissionError as e:
                print(f"ℹ️ 미션 중지 중 정보: {e}")

            await drone.mission.clear_mission()
            print("🗑️ 이전 미션 삭제 완료.")

            mission_items = [
                MissionItem(latitude,
                            longitude,
                            10, 10, True,
                            float('nan'), float('nan'),
                            MissionItem.CameraAction.NONE,
                            float('nan'), float('nan'),
                            float('nan'), float('nan'), float('nan'),
                            MissionItem.VehicleAction.NONE)
            ]
            mission_plan = MissionPlan(mission_items)
            await drone.mission.set_return_to_launch_after_mission(True)

            print("⏫ 새로운 미션 업로드 중...")
            await drone.mission.upload_mission(mission_plan)
            print("✅ 업로드 완료.")

            is_armed = False
            async for armed in drone.telemetry.armed():
                is_armed = armed
                break
            if not is_armed:
                print("드론이 Disarm 상태입니다. 다시 Arming 시도...")
                await drone.action.arm()

            print("🚀 미션 시작!")
            await drone.mission.start_mission()

        except Exception as e:
            print(f"🚨 미션 전환 중 오류 발생: {e}")

# 앱 실행 및 서버 시작
async def main():
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_post('/respond', respond)

    listener_task = asyncio.create_task(coordinate_listener())
    manager_task = asyncio.create_task(run_mission_manager())

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 5030)  # 포트 변경 가능
    print("웹 서버 시작: http://0.0.0.0:5030")
    await site.start()

    await asyncio.gather(listener_task, manager_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("프로그램 종료 중...")
