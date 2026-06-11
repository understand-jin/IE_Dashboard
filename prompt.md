아래 조건에 맞는 Streamlit CSV 챗봇 앱을 만들어줘.

## 기능 요구사항
- 로컬 CSV 파일을 고정 경로에서 읽어와서 (경로는 변수로 분리)
- Anthropic Claude API (claude-sonnet-4-20250514)를 사용해서
- 사용자가 데이터에 대해 질문하면 Claude가 답변하는 챗봇 UI를 Streamlit으로 만들어줘

## 데이터 처리
- CSV 전체 데이터를 Claude 시스템 프롬프트에 넣어줘 (전체 행 포함)
- 컨텍스트에는 전체 CSV, 수치형 통계, 품목유형별/납품상태별 건수 요약 포함
- 데이터는 앱 시작 시 한 번만 로드해서 st.session_state.context에 저장해두고 재사용

## 프롬프트 캐싱
- Anthropic 프롬프트 캐싱 적용 (cache_control: {"type": "ephemeral"})
- 시스템 프롬프트를 두 블록으로 구성:
  1. 역할 지시문 (캐싱 없음)
  2. CSV 데이터 컨텍스트 (cache_control 적용)
- 매 질문마다 캐시 읽기 토큰 수, 캐시 생성 토큰 수, 입력/출력 토큰 수 추적

## UI 구성
- 메인 화면: 데이터 로드 성공 메시지, 데이터 미리보기 expander, 채팅 인터페이스
- 사이드바: 누적 토큰 사용량 (입력/출력/캐시생성/캐시읽기), 캐시 적중률(%), 대화 초기화 버튼
- 채팅 히스토리는 st.session_state.messages로 관리 (다중 턴 대화 유지)

## 기타
- SSL 경고 억제 (urllib3.disable_warnings)
- CSV 인코딩 utf-8-sig
- API 키와 CSV 경로는 파일 상단 변수로 분리
- 시스템 프롬프트: 제약회사 SCM 데이터 분석 전문가 역할, 데이터 없으면 추측 금지, 숫자는 억/건 단위 표기