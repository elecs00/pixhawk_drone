# pixhawk_drone
 # pixhawk_drone

 이 저장소는 Pixhawk/ PX4 관련 드론 개발 및 시뮬레이션용 소스와 도구들을 모아놓은 프로젝트입니다.

 ## 전체 구조(요약)

 루트 폴더의 주요 항목과 역할을 아래에 정리합니다.

 ```
 / (repository root)
 ├─ QGroundControl-x86_64.AppImage      # (대형 바이너리) QGroundControl 실행파일
 ├─ PX4-Autopilot/                       # PX4 오토파일럿 소스 (대형, 서브모듈/내부 빌드 포함)
 ├─ px4_ros_uxrce_dds_ws/                # Micro XRCE DDS / ROS 관련 워크스페이스 (build, install, src 등)
 │  ├─ build/                            # 빌드 아티팩트 (커밋에서 제외되어야 함)
 │  ├─ install/                          # 설치 결과 (커밋에서 제외)
 │  └─ src/                              # 소스 코드
 ├─ px4_waypoint/                        # 사용자 작성한 waypoint / 웹 연동 스크립트
 ├─ px4_waypoint_v2/                     # waypoint 버전 2 (웹앱, 스크립트 등)
 ├─ rtk/                                 # RTK(정밀위치) 관련 스크립트
 ├─ PX4-ROS2-Gazebo-Drone-Simulation-Template/  # Gazebo + ROS2 시뮬레이션 템플릿
 └─ README.md                            # 이 파일
 ```

 ## 각 폴더 설명

 - `PX4-Autopilot/`
	 - PX4 오토파일럿 소스 코드가 들어있는 메인 디렉터리입니다.
	 - 빌드 결과(`build/`)나 서브모듈의 패키지 데이터가 포함되어 있을 수 있으므로 초기 푸시 시 주의하세요.

 - `px4_ros_uxrce_dds_ws/`
	 - Micro XRCE DDS와 관련된 ROS 워크스페이스입니다. `build/`, `install/`, `log/` 등 빌드 산출물이 포함됩니다.
	 - 일반적으로 `build/`, `install/`, `log/` 등은 `.gitignore`에 추가하여 소스만 관리합니다.

 - `px4_waypoint/`, `px4_waypoint_v2/`
	 - 사용자 제작 스크립트와 웹 앱(예: `drone_mission_web`)이 포함되어 있습니다.
	 - 프로젝트의 핵심 로직(경로 계획, 웹 연동 등)이 위치합니다.

 - `PX4-ROS2-Gazebo-Drone-Simulation-Template/`
	 - Gazebo와 ROS2 환경에서 PX4를 시뮬레이션하기 위한 템플릿과 설치 스크립트가 포함됩니다.

 - `QGroundControl-x86_64.AppImage`
	 - QGroundControl의 실행 가능한 AppImage 파일입니다. 파일 크기가 매우 크므로 일반적으로 Git에 포함시키지 않고 별도 저장소나 릴리스(Release)로 관리합니다.

 ## Git 관리 관련 권장사항

 - `.gitignore`에 다음 항목이 포함되어야 합니다:
	 - `build/`, `install/`, `log/` (워크스페이스 빌드 아티팩트)
	 - `*.AppImage`, `*.zip`, 대형 바이너리
	 - 편집기/OS 관련 파일 (`.vscode/`, `*.swp`, `.DS_Store` 등)

 - 대형 바이너리를 저장해야 한다면 Git LFS 사용을 권장합니다. (예: `git lfs track "*.AppImage"`)

 - 민감정보(API 키, 토큰 등)은 절대 커밋하지 마세요. 이미 푸시된 비밀이 있다면 즉시 레포지토리 히스토리에서 제거하고 토큰을 교체하세요.

 ## 간단 사용법

 로컬에서 프로젝트 루트로 이동한 뒤(이미 git이 설정된 경우):

 - 상태 확인:
 ```bash
 git status
 ```

 - 원격으로 푸시하기(SSH로 origin이 설정되어 있다면):
 ```bash
 git push origin main
 ```

 ## 기여 및 문의

 - 기여하실 경우 이슈(issue)를 열어 변경 목적을 설명해 주세요.
 - 협업 시 히스토리 재작성(force-push)를 한 경우, 다른 기여자는 로컬을 `git fetch` 후 `git reset --hard origin/main`로 동기화해야 합니다.

 ---

 (이 README는 프로젝트 구조를 빠르게 파악할 수 있도록 작성되었습니다. 더 자세한 설치/빌드 절차나 사용법을 원하시면 알려주세요.)
