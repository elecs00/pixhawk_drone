import time
from pymavlink import mavutil
from pyrtcm import RTCMMessage  # 'crc24q' 임포트 제거

def create_rtcm_1005(lat, lon, alt):
    """
    RTCM 1005 메시지(기지국 위치)를 생성합니다.
    .serialize()가 체크섬을 자동으로 처리합니다.
    """
    # 페이로드는 여전히 유효한 데이터가 아니므로 RTK Fixed 상태로 진입하지 못할 수 있습니다.
    # 이것은 메시지 구조와 전송 테스트를 위한 예시입니다.
    payload = b'\x3e\xd0\x00\x03\x8a\x56\x78\x90\x12\x34\x56\x78\x90\x12\x34\x56\x78\x90\x12\x34'
    msg = RTCMMessage(payload=payload)
    return msg.serialize() # 이 메서드가 내부적으로 CRC 계산을 수행합니다.


def main():
    # PX4 SITL에 UDP로 연결 (기본 포트: 14540)
    master = mavutil.mavlink_connection('udpout:localhost:14540')
    print("PX4 SITL에 연결 대기 중...")
    master.wait_heartbeat()
    print("하트비트 수신! 시스템 ID: %u, 컴포넌트 ID: %u" % (master.target_system, master.target_component))

    # 가상 기지국 위치
    base_lat = 47.397742
    base_lon = 8.545594
    base_alt = 488.0

    while True:
        rtcm_1005 = create_rtcm_1005(base_lat, base_lon, base_alt)
        
        # GPS_RTCM_DATA 메시지 전송
        master.mav.gps_rtcm_data_send(
            len(rtcm_1005),
            rtcm_1005
        )
        print(f"RTCM 메시지 전송됨 (길이: {len(rtcm_1005)} bytes)")
        time.sleep(1)

if __name__ == "__main__":
    main()
