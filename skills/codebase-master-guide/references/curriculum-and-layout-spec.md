# Codebase Master Guide: Curriculum & Layout Specification

본 문서는 백엔드 및 풀스택 코드베이스를 분석하여 대화형 마스터 슬라이드북(Interactive Slidebook)을 제작할 때 준수해야 하는 상세 기술 명세서입니다.

---

## 1. 12단계 표준 커리큘럼 명세 (Curriculum Specification)

### CH.00 온보딩 & 인프라 아키텍처 (Infrastructure Blueprint)
1. **Slide 0: 마스터 대시보드**
   - 4대 엔터프라이즈 메트릭스 (슬라이드 수, 소스코드 커버리지 100%, 망 분리 티어 수, STW 지연)
   - 4대 학습 트랙 (인프라 / 식별자 / 전수코드 / 엣지 시나리오)
   - 키보드 내비게이션 단축키 안내 바
2. **Slide 1: [인프라 토폴로지] C4 Deployment View**
   - 5대 네트워크 망 분리 (ZONE 1 클라이언트 ➔ ZONE 2 DMZ WAF/ALB ➔ ZONE 3 내부 App 파드 ➔ ZONE 4 데이터 원장 DB ➔ ZONE 5 외부 통신 채널)
   - 하단 패널: 4대 엔터프라이즈 인프라 보안 및 전자금융감독규정 준수 지침 (망 간 단방향 통신, DB 풀 격리, HSM 서명, mTLS)
3. **Slide 2: [E2E 데이터 흐름 & 트랜잭션 바운더리]**
   - 4단계 라이프사이클 (30ms 동기 접수 ➔ Netty 논블로킹 I/O ➔ 비동기 채굴 ➔ 0.1ms 멱등 인박스 수신)
   - 하단 패널: 단일 `@Transactional` vs 비동기 Outbox 패턴 비교 분석표 (커넥션 점유, 타임아웃 장애 격리, QPS 처리량)
4. **Slide 3: [고가용성 & 분산 코디네이션]**
   - 분산 환경 동시성 충돌(Distributed Cron Problem) vs ShedLock 원자적 행 잠금
   - 3단계 무인 자가치유 엔진 (FAILED 재시도 / UNKNOWN 단건조회 / 2h Long-Pending 웹훅유실 감지)
   - 하단 패널: ShedLock DDL 스키마 및 무정지 파라미터(`lockAtMostFor="55m"`, `lockAtLeastFor="10s"`) 튜닝 가이드
5. **Slide 4: [장애 대응 & DR 매트릭스]**
   - 5대 프로덕션 장애 시나리오별 인프라 방어 명세 표 (타임아웃, 웹훅 폭풍, 광클 연타, DB 풀 고갈, 체인 Reorg)
   - 하단 패널: 장애 대응 3단계 에스컬레이션 프로토콜 (Tier 1 무인치유 / Tier 2 관리자 수동개입 / Tier 3 원장실사 대사)
6. **Slide 5: 2대 모듈 구조 및 패키지 맵**
   - `api` 모듈(웹, 인증, 클라이언트, 스케줄러) vs `core` 모듈(엔티티, 원장, TSID 채번기)
   - 하단 패널: 클린 아키텍처 의존성 단방향 규칙 & 모듈 간 불변식 가이드

---

### CH.01 식별자 & 도메인 데이터 모델 지도 (Identifier Mapping)
1. **Slide 6: 사용자 3대 ID**
   - `dgtId` (교보 회원 식별자, 1급 개인정보, 외부 유출 원천 차단)
   - `userId` (내부 RDBMS PK, 64비트 TSID, 외래키 조인 성능 최적화)
   - `partnerUserId` (외부 가명화 키, AES-256 암호문, 블록체인 전송 전용)
   - 하단 패널: 실시간 변환 흐름도 & 개인정보보호법 '잊힐 권리' 준수 가이드
2. **Slide 7: 발행 추적 3대 ID**
   - `issuanceRequestId` (내부 DB PK, 영구 불변 접수증, 클라이언트 반환값)
   - `ohiRequestId` (외부 멱등 통신 키, 재시도 시마다 신규 TSID 채번하여 캐시 충돌 우회)
   - `eventId` (웹훅 인박스 고유 키, Unique Index 기반 중복 웹훅 0.1ms 차단)
   - 하단 패널: 재시도 발생 시 3대 ID의 생명주기 전이 매트릭스

---

### CH.02 ~ CH.07 핵심 6대 파일 100% 전수 코드 리뷰
- 선정한 6개 파일은 20~30행 단위로 슬라이드를 분할하며 한 줄도 생략하지 않습니다.
- 각 코드 슬라이드는 반드시:
  1. `startLine`, `highlightLines` (핵심 로직 라인 강조)
  2. PrettyLights 구문 강조 토큰 클래스 적용
  3. 사수의 1:1 라인 코칭 노트 배열 (`comments: [{ line, text }]`)

---

### CH.10 실무 3대 프로덕션 엣지 시나리오
1. **Slide 44: 시나리오 1 (광클 연타 동시성 방어)**
   - 4단계 타임라인: 0ms 1차 클릭 ➔ +15ms 2차 클릭 감지 ➔ +20ms duplicate=true 차단 ➔ 최종 단 1건 채굴
   - 하단 패널: 실제 운영 로그 비교 및 DB 행 상태 전이 다이어그램
2. **Slide 45: 시나리오 2 (외부 호출 소켓 타임아웃)**
   - 4단계 타임라인: 10초 타임아웃 ➔ UNKNOWN 상태 격리 ➔ O-HI 단건 API 조회 ➔ 404 재발행 or 200 원장 보정
   - 하단 패널: 타임아웃을 즉시 FAILED로 처리하면 안 되는 이유 & 4대 HTTP 상태 판정 매트릭스
3. **Slide 46: 시나리오 3 (2시간 웹훅 유실 무인 자가치유)**
   - 4단계 타임라인: 2시간 경과 감지 ➔ O-HI 배치 상태 질의 ➔ markSuccess 강제 원장 보정 ➔ Holding 테이블 연동
   - 하단 패널: 무인 자동치유 아키텍처의 비즈니스 가치 & 장기 펜딩 감지 SQL 쿼리

---

### CH.11 16대 실무 함정 매트릭스
- **Slide 47 (1~8번)**: PENDING 오해, FAILED 재시도 가능성, A40900 재귀 시 retryCount 불변, markSuccess 과거 실패사유 잔존, 동일 eventId 웹훅 스킵, PROCESSED != Holding 생성 100%, 스케줄러 보정 시 saveNftHoldings 미호출, 지갑 목록 노출 정책 매핑 조건.
- **Slide 48 (9~16번)**: ShedLock 실제 점유 시간의 오해(55m), ControllerTest 인증 검증 한계, ID 2회 채번의 숨은 이유, REQUESTED 사전 저장(Outbox), Service 트랜잭션 부재 이유(HikariCP), partnerUserId 캐싱 규칙, BigInteger 토큰 ID 필연성(uint256), 단일 발행 차단 범위의 조건부 동작.

---

### CH.12 자가진단 퀴즈 스테이션 & 온보딩 수료 대시보드
- **Slide 49~51 (퀴즈 1~3)**:
  - 질문 카드: 난이도 ⭐⭐⭐, 핵심 질문
  - 정답 및 근거 인터랙티브 토글: 사수 정답, 파일 및 라인 번호 인용
  - 보조 패널: 주니어 코드리뷰 관점 체크포인트 + **[관련 소스코드 슬라이드 바로가기]** 버튼
- **Slide 52 (수료 대시보드)**:
  - 수료 축하 배너
  - 6대 핵심 컴포넌트 마스터리 카드 (Controller, Service, Entity, Webhook, Scheduler, Test)
  - 프로덕션 배포 전 필수 7대 인프라 & 보안 체크리스트

---

## 2. 디자인 및 레이아웃 토큰 표준

### GitHub Primer & PrettyLights CSS Tokens
```css
/* Dark Mode */
.theme-dark {
  --bg-main: #0d1117;
  --bg-deck: #161b22;
  --bg-card: #161b22;
  --bg-subtle: #21262d;
  --border: #30363d;
  --border-focus: #388bfd;
  --text-title: #f0f6fc;
  --text-body: #c9d1d9;
  --text-muted: #8b949e;
  
  --code-bg: #0d1117;
  --code-border: #30363d;
  --code-text: #e6edf3;
  --gutter-num: #6e7681;
  --gutter-active: #f0f6fc;
  --highlight-bg: rgba(56, 139, 253, 0.15);
  --highlight-border: #388bfd;
  --line-hover: rgba(110, 118, 129, 0.15);

  --tok-kw: #ff7b72;
  --tok-anno: #d2a8ff;
  --tok-type: #79c0ff;
  --tok-method: #d2a8ff;
  --tok-str: #a5d6ff;
  --tok-const: #79c0ff;
  --tok-num: #79c0ff;
  --tok-bool: #ff7b72;
  --tok-comment: #8b949e;
  --tok-op: #e6edf3;
}

/* Light Mode */
.theme-light {
  --bg-main: #f6f8fa;
  --bg-deck: #ffffff;
  --bg-card: #f6f8fa;
  --bg-subtle: #ffffff;
  --border: #d0d7de;
  --border-focus: #0969da;
  --text-title: #1f2328;
  --text-body: #24292f;
  --text-muted: #656d76;
  
  --code-bg: #ffffff;
  --code-border: #d0d7de;
  --code-text: #1f2328;
  --gutter-num: #8c959f;
  --gutter-active: #1f2328;
  --highlight-bg: #ddf4ff;
  --highlight-border: #0969da;
  --line-hover: rgba(175, 184, 193, 0.2);

  --tok-kw: #cf222e;
  --tok-anno: #8250df;
  --tok-type: #0550ae;
  --tok-method: #8250df;
  --tok-str: #0a3069;
  --tok-const: #0550ae;
  --tok-num: #0550ae;
  --tok-bool: #cf222e;
  --tok-comment: #57606a;
  --tok-op: #1f2328;
}
```

### 펄스 애니메이션 (Pulse Focus Animation)
코칭 카드 클릭 시 해당 코드 라인으로 이동하며 1.8초간 시각적 집중 효과를 제공합니다:
```css
@keyframes pulseLineFocus {
  0% { background-color: rgba(56, 139, 253, 0.45); box-shadow: 0 0 15px rgba(56, 139, 253, 0.6); }
  50% { background-color: rgba(56, 139, 253, 0.25); box-shadow: 0 0 8px rgba(56, 139, 253, 0.3); }
  100% { background-color: var(--highlight-bg); box-shadow: none; }
}
.code-line-row.pulse-focus {
  animation: pulseLineFocus 1.8s ease-out forwards !important;
  border-left: 3px solid var(--highlight-border) !important;
}
```
