#!/usr/bin/env python3
import asyncio
from mavsdk import System
from mavsdk.mission import (MissionItem, MissionPlan)

async def run():
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
    mission_items.append(MissionItem(47.398039859999997,
                                     8.5455725400000002,
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
                                     MissionItem.VehicleAction.NONE)) # 이 부분이 추가되었습니다.
    mission_items.append(MissionItem(47.398036222362471,
                                     8.5463378339462299,
                                     10,
                                     10,
                                     True,
                                     float('nan'),
                                     float('nan'),
                                     MissionItem.CameraAction.NONE,
                                     float('nan'),
                                     float('nan'),
                                     float('nan'),
                                     float('nan'),
                                     float('nan'),
                                     MissionItem.VehicleAction.NONE)) # 이 부분이 추가되었습니다.

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
    # 실제 미션 완료를 확인하는 더 좋은 방법은 mission_progress를 모니터링하는 것입니다.
    print("미션 진행 중... (완료되거나 30초 후 종료)")
    await asyncio.sleep(900)
    print("종료.")

if __name__ == "__main__":
    # DeprecationWarning을 해결하기 위해 asyncio.get_event_loop() 대신 아래와 같이 사용합니다.
    asyncio.run(run())
