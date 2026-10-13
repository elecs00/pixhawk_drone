# pixhawk_drone — 안드로이드·웹 연동 PX4 드론 임무 제어

안드로이드 앱이 보낸 좌표를 받아 PX4 드론에 웨이포인트 임무를 올리고, 웹 관제 화면에서 정찰·긴급 출동을 지휘하는 MAVSDK 기반 스크립트 모음입니다. PX4 SITL(Gazebo) 시뮬레이션 환경에서 개발했습니다.

| 항목 | 내용 |
|---|---|
| 비행 제어 | PX4 Autopilot (Pixhawk), SITL + Gazebo 시뮬레이션 |
| 통신 | MAVSDK-Python (`udp://:14540`), pymavlink, UDP(안드로이드 → PC) |
| 웹 | Flask, aiohttp |
| 직접 구현 | `px4_waypoint/` 아래 전부 (임무 생성·업로드, 안드로이드 좌표 수신, 웹 관제, RTK 보정 메시지 시험) |

### 동작 흐름 (웹 관제 `drone_mission_web`)

```
안드로이드 앱 ──UDP 5005 "위도,경도"──▶ app.py ──MAVSDK──▶ PX4 (임무 업로드·시작·일시정지)
웹 브라우저(:1717) ──정찰 웨이포인트 설정 / 상태 조회──▶ app.py
정찰: 웨이포인트 임무 업로드 → 비행 → 임무 종료 후 자동 귀환(RTL)
긴급 좌표 수신 시: 진행 중인 정찰 일시정지 → goto 로 긴급 지점(고도 20m) 출동 → 도착 후 귀환(RTL)
```

## 📁 파일 구조

```
pixhawk_drone/
└── px4_waypoint/
    ├── px4_waypoint_v1/px4_waypoint.py       # v1: 코드에 고정된 웨이포인트로 임무 비행
    ├── px4_waypoint_v2/
    │   ├── px4_waypoint.py                   # v2: 안드로이드에서 UDP 로 받은 좌표로 임무 비행
    │   └── drone_mission_web/
    │       ├── app.py                        # 최종: 웹 관제 (정찰 + 긴급 출동), 포트 1717
    │       ├── app_v1.py                     # app.py 의 이전 동작 버전
    │       └── templates/index.html          # 관제 화면
    ├── web_px4.py                            # 좌표 수신 → 웹에서 YES/NO 승인 → 임무 실행, 포트 5030
    └── rtk/rtk.py                            # RTCM 1005(기준국 위치) 메시지를 MAVLink 로 주입하는 시험
```

## 🛠️ 필요한 외부 소프트웨어

이 저장소에는 아래 외부 소스를 넣지 않습니다. 개발 당시 쓰던 커밋을 기록해 둡니다.

| 소프트웨어 | 원본 저장소 | 당시 커밋 |
|---|---|---|
| PX4 Autopilot | https://github.com/PX4/PX4-Autopilot | `8625a902f7a50bb0cd27381dc8f91abda66699ba` |
| Micro XRCE-DDS Agent | https://github.com/eProsima/Micro-XRCE-DDS-Agent | `57d086216d01ec43121845d385894a25987f8a2c` (v2.4.2) |
| PX4-ROS2-Gazebo 시뮬레이션 템플릿 | https://github.com/SathanBERNARD/PX4-ROS2-Gazebo-Drone-Simulation-Template | `2dc9ca941628b72bde407068829019af9d078dba` |
| QGroundControl | https://docs.qgroundcontrol.com/master/en/qgc-user-guide/getting_started/download_and_install.html | — |

## 🚀 실행 방법 (시뮬레이션 기준)

1. PX4 SITL 실행
   ```bash
   cd PX4-Autopilot
   make px4_sitl gz_x500
   ```
2. 파이썬 의존성 설치
   ```bash
   pip3 install mavsdk flask aiohttp pymavlink pyrtcm
   ```
3. 웹 관제 실행
   ```bash
   cd px4_waypoint/px4_waypoint_v2/drone_mission_web
   python3 app.py
   ```
4. 브라우저에서 `http://<PC 주소>:1717` 접속
5. 안드로이드 앱(또는 아래 명령)으로 좌표 전송
   ```bash
   echo -n "47.3980,8.5460" | nc -u -w1 <PC 주소> 5005
   ```

> `rtk/rtk.py` 의 기준국 좌표(47.3977, 8.5456)는 PX4 SITL 기본 위치(취리히)입니다. 실제 기체에 쓸 때는 실제 기준국 좌표로 바꿔야 합니다.
