#!/usr/bin/env python3
import asyncio
from mavsdk import System
from mavsdk.mission import (MissionItem, MissionPlan)
import socket

async def receive_coordinates():
    # UDP 소켓 생성 및 바인딩
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 5005)) # 모든 IP로부터 5005번 포트로 수신 대기
    print("안드로이드 앱으로부터 좌표 수신 대기 중...")
    
    # 데이터 수신 (비동기 처리)
    loop = asyncio.get_event_loop()
    data, addr = await loop.run_in_executor(None, sock.recvfrom, 1024)
    
    # 수신된 데이터를 문자열로 디코딩
    received_data = data.decode('utf-8').strip()
    print(f"좌표 수신: {received_data}")
    
    # 위도와 경도 파싱
    lat_str, lon_str = received_data.split(',')
    latitude = float(lat_str)
    longitude = float(lon_str)
    
    return latitude, longitude

async def run():
    # 안드로이드 앱으로부터 좌표 수신
    latitude, longitude = await receive_coordinates()

    # 드론에 연결 (SITL은 UDP 14540 포트 사용)
    drone = System()
    await drone.connect(system_address="udp://:14540")

    print("드론 연결 대기 중...")
    async for state in drone.telemetry.health():
        if state.is_global_position_ok and state.is_home_position_ok:
            print("드론 위치 확인 완료")
            break

    print("미션 아이템 생성 중...")
    mission_items = []
    # 위도, 경도, 상대 고도, 속도, 수락 반경 등 설정
    mission_items.append(MissionItem(latitude,
                                     longitude,
                                     10, # 고도 (미터)
                                     10, # 속도 (m/s)
                                     True, # is_fly_through
                                     float('nan'),
                                     float('nan'),
                                     MissionItem.CameraAction.NONE,
                                     float('nan'),
                                     float('nan'),
                                     float('nan'),
                                     float('nan'),
                                     float('nan'),
                                     MissionItem.VehicleAction.NONE))

    # 미션 플랜 생성
    mission_plan = MissionPlan(mission_items)

    # 드론에 미션 업로드
    await drone.mission.set_return_to_launch_after_mission(True)
    print("미션 업로드 중...")
    await drone.mission.upload_mission(mission_plan)
    print("업로드 완료")

    # 드론 시동(Arm)
    print("드론 시동(Arming)...")
    await drone.action.arm()

    # 미션 시작
    print("미션 시작!")
    await drone.mission.start_mission()

    # 미션이 끝날 때까지 대기
    print("미션 진행 중...")
    await asyncio.sleep(900)
    print("종료.")

if __name__ == "__main__":
    asyncio.run(run())
