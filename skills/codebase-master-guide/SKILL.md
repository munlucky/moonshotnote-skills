---
name: codebase-master-guide
description: >-
  코드베이스 전수 분석 및 인터랙티브 개발자 가이드(슬라이드북) 제작 스킬.
  주니어 개발자 눈높이의 "Why(기술적 이유)" 중심 해설, C4 인프라 토폴로지(5대 망 분리),
  E2E 트랜잭션 바운더리, 100% 전수 소스코드 리뷰(라인별 사수 1:1 코칭 노트 매핑),
  하단 빈 공간(Dead Space) 제로 2-Tier 레이아웃, 3대 엣지 시나리오, 16대 실무 함정 매트릭스,
  자가진단 퀴즈 스테이션을 포함한 단일 Standalone HTML을 자동 생성합니다.
---

# Codebase Master Guide Skill

## 1. 목적 및 사용 시점 (Use When)

Use this skill when the user asks to:
- analyze any backend or full-stack codebase and create a comprehensive developer onboarding handbook
- generate an interactive, zero-dependency slide-based developer guide (master slidebook HTML)
- conduct a line-by-line, 100% coverage code review with senior 1:1 coaching notes
- explain enterprise infrastructure topology, network isolation, Outbox patterns, and distributed locks

Trigger phrases:
- `$codebase-master-guide`
- `코드베이스 분석 가이드 만들어줘`
- `개발자 가이드 슬라이드북 제작`
- `전수 코드 리뷰 문서 만들어줘`
- `인터랙티브 슬라이드북 생성`
- `master slidebook`
- `codebase master guide`
- `프로젝트 전수 코드 리뷰 가이드`

## 2. 제외 및 라우팅 기준 (Route Away)

- 단순 1개 파일의 작은 변경사항 diff 설명만 필요한 경우 ➔ `explain-diff-html`로 라우팅.
- 신규 아키텍처 의사결정(ADR)이나 PRD 설계 단계인 경우 ➔ `moonshot-architecture`로 라우팅.
- 새로운 기능을 직접 구현하거나 리팩터링을 수행하는 경우 ➔ `moonshot-orchestrator`로 라우팅.

---

## 3. 핵심 4대 원칙 (Core Principles)

1. **Why(기술적 당위성) 중심 해설**: 단순 문법 설명(`"A를 호출합니다"`)을 엄격히 배제하고, "왜 이 어노테이션이 필요한가?", "왜 DB PK와 외부 호출 ID를 분리하는가?", "장애 시 커넥션 풀에 어떤 영향이 있는가?"를 규명합니다.
2. **100% 전수 코드 리뷰 (Zero Code Omission)**: 선정한 핵심 6대 파일은 생략 부호(`...`) 없이 1행부터 마지막 행까지 20~30행 단위로 분할하여 전수 수록하고 라인별 코칭 노트를 매핑합니다.
3. **하단 빈 공간(Dead Space) 제로 법칙 (2-Tier Vertical Structure)**: 슬라이드 뷰포트(`87vh`)에서 본문이 상단에만 쏠리고 하단이 텅 비는 문제를 원천 차단합니다. 상단 60% 대형 도식화 + 하단 40% 엔터프라이즈 심층 지식 패널(비교 분석표, SOP 매뉴얼, 튜닝 가이드)을 반드시 결합합니다.
4. **가로 스크롤 절대 금지 (`overflow-x: hidden !important; max-width: 100vw;`)**: 어떤 해상도(모바일, 태블릿, FHD, QHD, 4K)에서도 브라우저 가로 스크롤바가 절대 발생하지 않아야 합니다.

---

## 4. 12단계 표준 커리큘럼 아키텍처 (12-Chapter Formula)

새로운 코드베이스를 분석할 때는 다음 12개 챕터 골격을 필수 적용합니다:

| 챕터 | 제목 | 주요 구성 요소 |
| :--- | :--- | :--- |
| **CH.00** | **온보딩 & 인프라 아키텍처** | • 전역 온보딩 대시보드 & 4대 트랙<br>• [인프라 토폴로지] C4 Deployment View (5대 네트워크 망 분리: ZONE 1~5)<br>• [E2E 데이터 흐름] 30ms 동기 접수 ➔ Outbox ➔ 채굴 ➔ 웹훅 최종 일관성<br>• [고가용성 & 분산 코디네이션] ShedLock 분산 락 & 3단계 자가치유 인프라<br>• [장애 대응 DR 매트릭스] 5대 장애 시나리오별 인프라 방어 명세 표<br>• 2대 모듈 구조 및 패키지 맵 (Clean Architecture 의존성 규칙) |
| **CH.01** | **식별자 & 데이터 모델 지도** | • 사용자 3대 ID: `dgtId` vs `userId` vs `partnerUserId` (개인정보보호법 잊힐 권리 준수)<br>• 발행 추적 3대 ID: `issuanceRequestId` vs `ohiRequestId` vs `eventId` (멱등성 분리 원칙) |
| **CH.02** | **진입점 Controller 전수 리뷰** | • REST 엔드포인트 선언, 헤더 인증 토큰 수신, HTTP 202 ACCEPTED 비동기 접수 |
| **CH.03** | **오케스트레이션 Service 전수 리뷰** | • Outbox 패턴 DB 선기록, 광클 방지 멱등성 가드, Netty WebClient 논블로킹 I/O, 재귀 재시도 |
| **CH.04** | **도메인 원장 Entity 전수 리뷰** | • JPA 복합 인덱스, 유니크 제약조건, 캡슐화된 정적 팩토리, 4총사 상태 전이 불변식 |
| **CH.05** | **비동기 Webhook 수신부 전수 리뷰** | • HMAC-SHA512 서명 검증, Webhook Inbox DB 유니크 인덱스 기반 0.1ms 중복 차단 |
| **CH.06** | **분산 배치 Scheduler 전수 리뷰** | • ShedLock 다중 파드 중복 실행 방어, 3단계 무인 자가치유 파이프라인 (FAILED/UNKNOWN/2h유실) |
| **CH.07** | **단위 테스트(Test) 전수 리뷰** | • MockMvc 컨트롤러 슬라이스 테스트, 의존성 모킹, Spring REST Docs 자동 문서화 |
| **CH.08~09** | **부가 도메인 & 보안 필터** | • 어드민 서비스, 발행 정책 엔티티, AES 대칭키 암복호화 필터 |
| **CH.10** | **실무 3대 프로덕션 엣지 시나리오** | • 시나리오 1: 광클(연타) 시 4단계 멱등 차단 타임라인 & 실제 운영 로그<br>• 시나리오 2: 소켓 타임아웃 발생 시 UNKNOWN 격리 및 실상태 조회 매트릭스<br>• 시나리오 3: 2시간 웹훅 패킷 유실 시 ShedLock 무인 감지 및 원장 강제 보정 |
| **CH.11** | **16대 실무 함정 매트릭스** | • 기획서 vs 실제 코드 불일치 1~8번 (PENDING 오해, FAILED 재시도, eventId 스킵 등)<br>• 운영 및 인프라 연동 함정 9~16번 (ShedLock 점유시간, 트랜잭션 부재 이유, uint256 등) |
| **CH.12** | **자가진단 퀴즈 & 수료 대시보드** | • 실무 역량 자가진단 퀴즈 1~3 (문제, 사수 모범 정답, 코드 근거, 소스코드 퀵 점프)<br>• 온보딩 수료 배너 & 6대 핵심 컴포넌트 마스터리 & 배포 전 7대 체크리스트 |

---

## 5. UI/UX 및 코드 뷰어 엔진 규격

### 5-1. 레이아웃 & 데드스페이스 해소 (2-Tier Vertical System)
- 모든 `card` 슬라이드는 컨테이너에 `h-full min-h-[calc(85vh-150px)] flex flex-col justify-between`을 적용합니다.
- 상단 도식화 카드: `min-h-[380px] ~ min-h-[430px]`, `p-6 md:p-8`, 제목 `text-lg md:text-xl font-black`, 본문 `text-sm md:text-base`.
- 하단 심층 패널: 비교 분석표(`table`), 보안/SLA 지침(Grid 3~4), SOP 매뉴얼, 로그 분석기 배치.

### 5-2. 소스코드 뷰어 (GitHub Primer & PrettyLights)
- **공식 컬러 토큰**: `--tok-kw` (#ff7b72/#cf222e), `--tok-anno` (#d2a8ff/#8250df), `--tok-type` (#79c0ff/#0550ae), `--tok-str` (#a5d6ff/#0a3069), `--tok-comment` (#8b949e/#57606a).
- **고대비 라인 거터**: 너비 `4rem`, 행 호버 시 강조, 클릭 시 해당 라인의 코칭 카드로 자동 스크롤.
- **사수의 1:1 코칭 카드**: 우측(또는 하단)에 배치. 카드 클릭 시 해당 코드 라인으로 스크롤 이동 및 `pulseLineFocus` 애니메이션(푸른색 글로우 1.8초) 실행.
- **6대 툴바**: A-/A+ 폰트 줌(`13px~24px`), 줄바꿈 토글(↩), 레이아웃 전환(분할 뷰 7:5 / 와이드 뷰 12열), 실시간 인코드 검색(🔍, `<mark>` 하이라이트), 전체화면 모달(⛶), 원클릭 코드 복사(📋).

### 5-3. 자가진단 퀴즈 스테이션
- 문제 카드: 질문 헤더 `text-xl md:text-2xl font-black`, 출제 태그, 난이도 뱃지.
- 인터랙티브 토글: `[👉 사수의 정답 & 코드 근거 확인]` 클릭 시 정답과 `ClassName.java:LineNum` 인용 박스 노출.
- 보조 2열: 좌측 주니어 PR 리뷰 체크포인트, 우측 **`[관련 소스코드 슬라이드 바로가기 ➔]`** 점프 버튼.

---

## 6. 신규 코드베이스 분석 5단계 실행 프로세스 (Procedure)

1. **Step 1: 정적 탐색 및 6대 핵심 파일 선정**
   - 진입점(Controller/Handler) ➔ 오케스트레이션(Service/UseCase) ➔ 원장(Entity/Model) ➔ 비동기 수신(Webhook/Consumer) ➔ 스케줄러(Scheduler/Cron) ➔ 테스트(Test/Spec).
2. **Step 2: 인프라 토폴로지 및 트랜잭션 경계 작성**
   - 네트워크 망 분리(DMZ/App/DB/HSM/Chain), 인그레스 WAF, HikariCP 커넥션 풀, 타임아웃 예산 도출.
3. **Step 3: 식별자 및 데이터 모델 변환 지도 작성**
   - 회원 식별자, 내부 PK, 외부 멱등 키, 암호화 가명화 키 변환 흐름 정리.
4. **Step 4: 파일별 전 라인 파싱 및 슬라이드 스펙 JSON 생성**
   - 20~30행 단위 분할, 핵심 라인 하이라이트 번호 목록, 사수의 1:1 코칭 노트 작성.
5. **Step 5: `scripts/render_slidebook.py` 실행 및 가이드 생성**
   - `python scripts/render_slidebook.py spec.json -o <project-name>-guide.html` 실행하여 단일 배포용 HTML 생성.
   - 브라우저 검증 및 가로 스크롤, 내비게이션, 퀴즈 토글 동작 확인.

---

## 7. 하드 스톱 및 품질 체크리스트 (Hard Stops)

- [ ] **코드 누락 금지**: 6대 핵심 소스코드 슬라이드에 생략 부호(`...`)가 포함되지 않았는가?
- [ ] **가로 스크롤 제로**: `overflow-x: hidden !important; max-width: 100vw;`가 적용되어 모바일/PC 모두에서 가로 스크롤이 발생하지 않는가?
- [ ] **데드 스페이스 제로**: 비코드 슬라이드의 하단 40%에 엔터프라이즈 심층 지식 패널(비교표/체크포인트/SOP)이 채워져 있는가?
- [ ] **내비게이션 무결성**: 이전/다음 버튼, 키보드 방향키(`←`, `→`, `Space`), 전체 목차 모달(전체 슬라이드 전수 연동)이 100% 동작하는가?
- [ ] **보안 정보 노출 금지**: 실제 운영 DB 비밀번호, KMS 마스터 키, 개인정보 실명 데이터가 마스킹되었는가?
