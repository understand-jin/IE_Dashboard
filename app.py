import os
import streamlit as st
import pandas as pd
import anthropic
from utils import standard_data_processing, make_dw_summary, make_dwb_summary

# ── Output 파일 경로 ─────────────────────────────────────────
_OUT_NAMES = ["m0_dw","m1_dw","m2_dw","m3_dw","m0_dwb","m1_dwb","m2_dwb","m3_dwb","final_df"]
_OUT_PATHS = {n: f"Output_data/{n}.csv" for n in _OUT_NAMES}

def _data_exists() -> bool:
    return all(os.path.exists(p) for p in _OUT_PATHS.values())

def _load_from_output():
    dfs = {}
    for name in _OUT_NAMES:
        df = pd.read_csv(_OUT_PATHS[name], encoding="utf-8-sig")
        for col in ["납품일", "입고일"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        dfs[name] = df
    dw_df = pd.concat(
        [dfs["m0_dw"], dfs["m1_dw"], dfs["m2_dw"], dfs["m3_dw"]], ignore_index=True
    )
    return (
        dfs["m0_dw"], dfs["m1_dw"], dfs["m2_dw"], dfs["m3_dw"],
        dfs["m0_dwb"], dfs["m1_dwb"], dfs["m2_dwb"], dfs["m3_dwb"],
        dw_df, dfs["final_df"],
    )

def _process_and_save():
    result = standard_data_processing()
    (m0_dw, m1_dw, m2_dw, m3_dw,
     m0_dwb, m1_dwb, m2_dwb, m3_dwb, _dw_df, final_df) = result
    os.makedirs("Output_data", exist_ok=True)
    for name, df in [
        ("m0_dw", m0_dw), ("m1_dw", m1_dw), ("m2_dw", m2_dw), ("m3_dw", m3_dw),
        ("m0_dwb", m0_dwb), ("m1_dwb", m1_dwb), ("m2_dwb", m2_dwb), ("m3_dwb", m3_dwb),
        ("final_df", final_df),
    ]:
        df.to_csv(_OUT_PATHS[name], index=False, encoding="utf-8-sig")
    return result

st.set_page_config(page_title="납기준수율 대시보드", layout="wide")

FONT = "'Pretendard','Apple SD Gothic Neo','Noto Sans KR',sans-serif"

# ── 스틸 미니멀 CSS ────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600&display=swap');

html, body, [class*="css"] {{
    font-family: {FONT};
}}

.stApp {{
    background: #f5f7fa;
}}

.dash-header {{
    background: #fff;
    border-bottom: 2px solid #1567d3;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 20px;
    font-family: {FONT};
}}
.dash-header-icon  {{ font-size: 20px; color: #1567d3; }}
.dash-header-title {{ font-size: 18px; font-weight: 600; color: #1e2d4e; }}
.dash-header-sub   {{ font-size: 12px; color: #6b7280; margin-left: auto; }}

.metric-row {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 20px;
    font-family: {FONT};
}}
.metric-card {{
    background: #fff;
    border-radius: 10px;
    padding: 14px 16px;
    border-left: 4px solid #e2e8f0;
    border-top: 0.5px solid #e2e8f0;
    border-right: 0.5px solid #e2e8f0;
    border-bottom: 0.5px solid #e2e8f0;
}}
.metric-card .m-label {{
    font-size: 11px;
    font-weight: 500;
    color: #6b7280;
    margin-bottom: 5px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}
.metric-card .m-value {{
    font-size: 26px;
    font-weight: 600;
    line-height: 1.2;
}}

.section-title {{
    font-size: 13px;
    font-weight: 600;
    color: #5a6a8a;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 6px 0 10px 0;
    border-bottom: 0.5px solid #e2e8f0;
    margin-bottom: 14px;
    font-family: {FONT};
}}

.tbl-wrap {{
    border-radius: 10px;
    overflow: hidden;
    border: 0.5px solid #e2e8f0;
    margin-bottom: 20px;
    font-family: {FONT};
}}

.chat-panel-header {{
    background: #fff;
    border-bottom: 2px solid #1567d3;
    border-radius: 12px 12px 0 0;
    padding: 12px 18px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: {FONT};
}}
.chat-panel-header .ch-icon {{
    width: 28px; height: 28px;
    background: #eef2fa;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; color: #1567d3;
}}
.chat-panel-header .ch-title  {{ font-size: 14px; font-weight: 600; color: #1e2d4e; }}
.chat-panel-header .ch-status {{ font-size: 11px; color: #16a34a; margin-left: auto; }}

/* ─── 챗봇 메시지 스타일 ─── */
[data-testid="stChatMessage"] {{
    background: transparent !important;
    padding: 4px 0 !important;
}}
[data-testid="stChatMessageContent"] p {{
    font-size: 14px !important;
    line-height: 1.65 !important;
    font-family: {FONT} !important;
}}

/* ─── AI 말풍선 ─── */
[data-testid="stChatMessage"]:has(svg[data-testid="chatAvatarIcon-assistant"]) {{
    background: #fff !important;
    border: 0.5px solid #e4eaf5 !important;
    border-radius: 6px 14px 14px 14px !important;
    box-shadow: 0 1px 6px rgba(0,0,0,.05) !important;
    padding: 8px 14px !important;
    margin: 3px 0 8px 0 !important;
}}

/* ─── 입력창 ─── */
[data-testid="stChatInput"] textarea {{
    font-family: {FONT} !important;
    font-size: 13px !important;
    background: #f5f7fa !important;
    border: 0.5px solid #d1d9e6 !important;
    border-radius: 20px !important;
}}

/* ─── 사이드바 ─── */
[data-testid="stSidebar"] {{
    background: #fff;
    border-right: 0.5px solid #e2e8f0;
}}
[data-testid="stSidebar"] .stSlider label {{
    font-size: 13px !important;
    color: #1e2d4e !important;
    font-family: {FONT} !important;
}}

/* ─── Thinking dots ─── */
@keyframes thinkbounce {{
    0%, 100% {{ opacity: .2; transform: translateY(0); }}
    50%       {{ opacity: 1;  transform: translateY(-5px); }}
}}
.think-dot {{
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #1567d3;
    margin: 0 2px;
    animation: thinkbounce 1.2s ease-in-out infinite;
}}
.think-dot:nth-child(2) {{ animation-delay: .2s; }}
.think-dot:nth-child(3) {{ animation-delay: .4s; }}

/* ─── 커서 깜빡임 ─── */
@keyframes blink {{ 0%,100%{{opacity:1;}} 50%{{opacity:0;}} }}

/* ══════════════════════════════════════
   AI 응답 마크다운 스타일링
   ══════════════════════════════════════ */

/* 헤더 */
[data-testid="stChatMessageContent"] h1,
[data-testid="stChatMessageContent"] h2,
[data-testid="stChatMessageContent"] h3,
[data-testid="stChatMessageContent"] h4 {{
    font-family: {FONT} !important;
    color: #1567d3 !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    letter-spacing: .02em !important;
    text-transform: none !important;
    margin: 14px 0 6px 0 !important;
    padding-bottom: 5px !important;
    border-bottom: 1.5px solid #e2e8f0 !important;
}}

/* 마크다운 테이블 */
[data-testid="stChatMessageContent"] table {{
    border-collapse: collapse !important;
    width: 100% !important;
    margin: 10px 0 14px 0 !important;
    font-size: 12.5px !important;
    font-family: {FONT} !important;
    border-radius: 8px !important;
    overflow: hidden !important;
    border: 1px solid #e2e8f0 !important;
}}
[data-testid="stChatMessageContent"] thead tr {{
    background: #1e2d4e !important;
}}
[data-testid="stChatMessageContent"] th {{
    color: #fff !important;
    padding: 8px 12px !important;
    text-align: left !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    font-family: {FONT} !important;
    white-space: nowrap !important;
}}
[data-testid="stChatMessageContent"] tbody tr:nth-child(odd) td {{
    background: #fff !important;
}}
[data-testid="stChatMessageContent"] tbody tr:nth-child(even) td {{
    background: #f7f9ff !important;
}}
[data-testid="stChatMessageContent"] td {{
    padding: 7px 12px !important;
    border: 1px solid #e8edf5 !important;
    font-family: {FONT} !important;
    font-size: 12.5px !important;
    color: #1e2d4e !important;
}}

/* 리스트 */
[data-testid="stChatMessageContent"] ul,
[data-testid="stChatMessageContent"] ol {{
    margin: 6px 0 8px 0 !important;
    padding-left: 18px !important;
}}
[data-testid="stChatMessageContent"] li {{
    font-size: 13.5px !important;
    line-height: 1.7 !important;
    color: #2d3748 !important;
    margin-bottom: 2px !important;
}}

/* 블록쿼트 (결론/요약 강조) */
[data-testid="stChatMessageContent"] blockquote {{
    background: #eef4ff !important;
    border-left: 3px solid #1567d3 !important;
    border-radius: 0 8px 8px 0 !important;
    margin: 10px 0 !important;
    padding: 10px 14px !important;
    color: #1e2d4e !important;
}}
[data-testid="stChatMessageContent"] blockquote p {{
    font-size: 13px !important;
    font-weight: 500 !important;
    margin: 0 !important;
}}

/* 볼드 */
[data-testid="stChatMessageContent"] strong {{
    color: #1e2d4e !important;
    font-weight: 700 !important;
}}

/* 구분선 */
[data-testid="stChatMessageContent"] hr {{
    border: none !important;
    border-top: 1px solid #e2e8f0 !important;
    margin: 12px 0 !important;
}}

/* 인라인 코드 */
[data-testid="stChatMessageContent"] code {{
    background: #f0f4ff !important;
    color: #1567d3 !important;
    border-radius: 4px !important;
    padding: 1px 6px !important;
    font-size: 12px !important;
}}
</style>
""", unsafe_allow_html=True)


# ── 헤더 ──────────────────────────────────────────────────
st.markdown(f"""
<div class="dash-header">
    <span class="dash-header-icon">📋</span>
    <span class="dash-header-title">납기준수율 대시보드</span>
    <span class="dash-header-sub">수출입팀 · IE Dashboard</span>
</div>
""", unsafe_allow_html=True)


# ── 사이드바 ──────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f'<div style="font-size:15px;font-weight:600;color:#1e2d4e;'
        f'margin-bottom:14px;font-family:{FONT};">⚙️ 목표율 설정</div>',
        unsafe_allow_html=True,
    )
    dw_target  = st.slider("대웅제약 (DW) 목표율",  0, 100, 80, 1, format="%d%%") / 100
    dwb_target = st.slider("대웅바이오 (DWB) 목표율", 0, 100, 80, 1, format="%d%%") / 100
    st.divider()
    st.markdown(
        f'<div style="font-size:14px;font-weight:600;color:#1e2d4e;'
        f'margin-bottom:8px;font-family:{FONT};">🔄 데이터 처리</div>',
        unsafe_allow_html=True,
    )
    if _data_exists():
        import datetime
        _ts = os.path.getmtime(_OUT_PATHS["final_df"])
        _dt = datetime.datetime.fromtimestamp(_ts).strftime("%Y-%m-%d %H:%M")
        st.markdown(
            f'<div style="font-size:11px;color:#6b7280;margin-bottom:8px;font-family:{FONT};">'
            f'마지막 처리: {_dt}</div>',
            unsafe_allow_html=True,
        )
    if st.button("▶ 데이터 처리 실행", type="primary", use_container_width=True):
        with st.spinner("데이터 처리 중... (환율 조회 포함)"):
            try:
                _process_and_save()
                st.success("완료!")
                st.rerun()
            except Exception as _e:
                st.error(f"처리 오류: {_e}")
    st.divider()
    st.markdown(
        f'<div style="font-size:11px;color:#9ca3b0;font-family:{FONT};">'
        f'API 키는 .streamlit/secrets.toml에 설정하세요.</div>',
        unsafe_allow_html=True,
    )


# ── 헬퍼 함수 ────────────────────────────────────────────
def _period_label(df_list, fallback):
    for df in df_list:
        if len(df) > 0:
            return df["납품일"].dt.to_period("M").astype(str).iloc[0]
    return fallback


def _rate_pct(val):
    if not isinstance(val, str) or "%" not in val:
        return None
    try:
        return float(val.replace("%", "")) / 100
    except ValueError:
        return None


def _rate_color(val, target):
    r = _rate_pct(val)
    if r is None: return "#1e2d4e"
    if r >= target: return "#16a34a"
    if r >= target * 0.875: return "#e07b00"
    return "#c0392b"


def _rate_bg(val, target):
    r = _rate_pct(val)
    if r is None: return "#f5f7fa"
    if r >= target: return "#f0f9f4"
    if r >= target * 0.875: return "#fff8ec"
    return "#fef2f2"


def _accent_color(val, target):
    r = _rate_pct(val)
    if r is None: return "#e2e8f0"
    if r >= target: return "#16a34a"
    if r >= target * 0.875: return "#e07b00"
    return "#c0392b"


def metric_card(label, value, color="#1567d3", accent="#1567d3"):
    return (
        f'<div class="metric-card" style="border-left-color:{accent};">'
        f'<div class="m-label">{label}</div>'
        f'<div class="m-value" style="color:{color};">{value}</div>'
        f'</div>'
    )


def render_table(df, target):
    rate_cols = {c for c in df.columns if "납기준수율" in c}
    TH = (
        f"background:#1e2d4e;color:#fff;padding:10px 10px;"
        f"text-align:center;font-weight:600;white-space:nowrap;"
        f"border:1px solid #17243d;font-size:12px;font-family:{FONT};"
    )
    TD = (
        f"padding:8px 10px;text-align:center;"
        f"border:1px solid #e8edf5;white-space:nowrap;"
        f"font-size:13px;font-family:{FONT};"
    )
    parts = [f'<div class="tbl-wrap"><table style="width:100%;border-collapse:collapse;font-family:{FONT};">']
    parts.append("<thead><tr>")
    for col in df.columns:
        parts.append(f'<th style="{TH}">{col}</th>')
    parts.append("</tr></thead><tbody>")
    for i, (_, row) in enumerate(df.iterrows()):
        is_sub = (i == 0)
        row_bg = "#dbe9ff" if is_sub else ("#f4f8ff" if i % 2 == 1 else "#fff")
        row_fw = "font-weight:600;" if is_sub else ""
        parts.append("<tr>")
        for col in df.columns:
            raw = row[col]
            val = str(raw) if pd.notna(raw) else "-"
            if col == "목표":
                td = f"{TD}background:#eef2fa;{row_fw}color:#2563eb;font-weight:600;"
            elif col in rate_cols:
                rc = _rate_color(val, target)
                rb = _rate_bg(val, target)
                td = f"{TD}background:{rb};{row_fw}color:{rc};font-weight:600;"
            else:
                td = f"{TD}background:{row_bg};{row_fw}color:#1e2d4e;"
            parts.append(f'<td style="{td}">{val}</td>')
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "".join(parts)



# ── 데이터 로드 (Output_data 캐시에서 읽기) ──────────────────
data_loaded = False
m0_dw = m1_dw = m2_dw = m3_dw = None
m0_dwb = m1_dwb = m2_dwb = m3_dwb = None
dw_df = final_df = None

if not _data_exists():
    st.info("처리된 데이터가 없습니다. 사이드바의 **▶ 데이터 처리 실행** 버튼을 클릭하세요.")
    st.stop()

try:
    with st.spinner("데이터 불러오는 중..."):
        (m0_dw, m1_dw, m2_dw, m3_dw,
         m0_dwb, m1_dwb, m2_dwb, m3_dwb, dw_df, final_df) = _load_from_output()
    data_loaded = True
except Exception as e:
    st.error(f"데이터 로드 오류: {e}")
    st.exception(e)
    st.stop()

if not data_loaded:
    st.stop()


# ── 기간 라벨 & 요약 ──────────────────────────────────────
lbl1 = _period_label([m1_dw, m1_dwb], "전월")
lbl2 = _period_label([m2_dw, m2_dwb], "전전월")
lbl3 = _period_label([m3_dw, m3_dwb], "전전전월")

dw_result = make_dw_summary(
    m1_dw, lbl1,
    prev2_df=m2_dw,  prev2_label=lbl2,
    prev3_df=m3_dw,  prev3_label=lbl3,
    target_rate=dw_target,
)
dwb_result = make_dwb_summary(
    m1_dwb, lbl1,
    prev2_df=m2_dwb, prev2_label=lbl2,
    prev3_df=m3_dwb, prev3_label=lbl3,
    target_rate=dwb_target,
)

rate_col_1m  = f"납기준수율({lbl1})"
dw_sub       = dw_result.iloc[0]
dwb_sub      = dwb_result.iloc[0]
dw_rate_val  = dw_sub[rate_col_1m]
dwb_rate_val = dwb_sub[rate_col_1m]


# ── 지표 카드 4개 ─────────────────────────────────────────
st.markdown(f"""
<div class="metric-row">
    {metric_card("DW 납기준수율 " + lbl1, dw_rate_val,
                 _rate_color(dw_rate_val, dw_target),
                 _accent_color(dw_rate_val, dw_target))}
    {metric_card("DW 전체 건수",  f"{dw_sub['전체건수']}건",  "#1e2d4e", "#1567d3")}
    {metric_card("DWB 납기준수율 " + lbl1, dwb_rate_val,
                 _rate_color(dwb_rate_val, dwb_target),
                 _accent_color(dwb_rate_val, dwb_target))}
    {metric_card("DWB 전체 건수", f"{dwb_sub['전체건수']}건", "#1e2d4e", "#1567d3")}
</div>
""", unsafe_allow_html=True)


# ── 레이아웃: 왼쪽 테이블 / 오른쪽 챗봇 ──────────────────
col_left, col_right = st.columns([1.1, 0.9], gap="medium")

with col_left:
    st.markdown('<div class="section-title">대웅제약 (DW)</div>', unsafe_allow_html=True)
    st.markdown(render_table(dw_result, dw_target), unsafe_allow_html=True)

    st.markdown('<div class="section-title">대웅바이오 (DWB)</div>', unsafe_allow_html=True)
    st.markdown(render_table(dwb_result, dwb_target), unsafe_allow_html=True)


with col_right:
    # ── 챗봇 패널 헤더 ────────────────────────────────────
    st.markdown(f"""
    <div class="chat-panel-header">
        <div class="ch-icon">✨</div>
        <span class="ch-title">AI 분석 챗봇</span>
        <span class="ch-status">● 온라인</span>
    </div>
    """, unsafe_allow_html=True)

    # API 키 확인
    try:
        _api_key = st.secrets["ANTHROPIC_API_KEY"]
    except (KeyError, AttributeError):
        _api_key = ""

    if not _api_key:
        st.error("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        st.code('ANTHROPIC_API_KEY = "sk-ant-..."', language="toml")
        st.stop()

    # 세션 초기화
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    pending_input = None

    # ── 초기화 버튼 ──
    if st.button("🗑️ 대화 초기화", use_container_width=True):
        st.session_state.chat_messages = []
        st.rerun()

    # ── 시스템 프롬프트 ──
    @st.cache_data(show_spinner=False)
    def _build_system_prompt(df_csv):
        return f"""당신은 대웅제약/대웅바이오 수출입 납기준수율 분석 전문 AI입니다.
아래는 최근 4개월(당월 포함)의 구매오더 납품 원본 데이터입니다.

## 컬럼 설명
- 회사코드: 1200 = 대웅제약(DW), 1300 = 대웅바이오(DWB)
- 납품일: 오더 상 납품 예정일
- 납품상태: '정상' = 납기 준수, 그 외 = 미준수
- 입고일: 실제 입고(수령)일
- 입고금액(현지통화): 원화 환산 금액 (KRW)
- 자재내역: 자재들의 이름
- 구매오더: 구매오더 번호
- 오더수량: 발주한 수량
- 품목유형(DW 기준): 상품 / 반제 / 라이선스 / 비라이선스 / 오파드라이
- 품목유형(DWB 기준): 일반 / UDCA / 콜린 / 펙수 / 세파

## 납기준수율 계산식
납기준수율 = 납품상태 '정상' 건수 ÷ 전체 건수 × 100 (%)

## 데이터 (CSV 형식)
{df_csv}

## 답변 규칙
- **한국어**로 답변하세요.
- 데이터를 근거로 구체적 수치를 포함하세요.
- 데이터에 없는 내용은 "데이터에서 확인되지 않습니다"라고 답하세요.
- 답변은 간결하고 핵심만 담아주세요.

## 반드시 지킬 마크다운 형식
- **섹션 구분**: `###` 헤더 사용 (예: `### 📊 납기준수율 현황`)
- **표**: 반드시 파이프(`|`) 형식 사용
  ```
  | 구분 | 건수 | 납기준수율 |
  |------|------|-----------|
  | 전체 | 17건 | 52.9% |
  ```
- **핵심 수치**: **볼드** 처리 (예: 납기준수율 **52.9%**)
- **결론/요약**: `>` 블록쿼트로 강조
  ```
  > 💡 결론: 스타빅현탁액이 핵심 원인입니다.
  ```
- 순위/목록: 번호 또는 `-` 리스트 사용
- 구분선(`---`)으로 섹션 분리"""

    with open(_OUT_PATHS["final_df"], encoding="utf-8-sig") as _f:
        _df_csv = _f.read()
    _system_prompt = _build_system_prompt(_df_csv)

    # ── 대화 컨테이너 ──
    chat_container = st.container(height=620)
    with chat_container:
        if not st.session_state.chat_messages:
            st.markdown(f"""
            <div style="text-align:center;padding:60px 20px;color:#9ca3b0;font-family:{FONT};">
                <div style="font-size:36px;margin-bottom:12px;">✨</div>
                <div style="font-size:14px;font-weight:500;color:#5a6a8a;margin-bottom:6px;">
                    납기준수율 AI 분석 챗봇
                </div>
                <div style="font-size:12px;line-height:1.7;">
                    데이터 기반으로 질문에 답변드립니다.<br>
                    아래 입력창에 질문을 입력해보세요.
                </div>
            </div>
            """, unsafe_allow_html=True)
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # ── 입력 & 처리 ──
    typed_input = st.chat_input("납품 데이터에 대해 질문하세요...")
    final_input = pending_input or typed_input

    if final_input:
        st.session_state.chat_messages.append({"role": "user", "content": final_input})

        try:
            _client = anthropic.Anthropic(api_key=_api_key)
            _api_messages = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.chat_messages
            ]

            with chat_container:
                with st.chat_message("user"):
                    st.markdown(final_input)

                with st.chat_message("assistant"):
                    thinking = st.empty()
                    thinking.markdown(
                        f'<div style="padding:4px 0;font-family:{FONT};'
                        f'font-size:13px;color:#1567d3;">'
                        f'<span class="think-dot"></span>'
                        f'<span class="think-dot"></span>'
                        f'<span class="think-dot"></span>'
                        f'&nbsp; 분석 중입니다...</div>',
                        unsafe_allow_html=True,
                    )

                    with _client.messages.stream(
                        model="claude-sonnet-4-6",
                        max_tokens=2048,
                        system=[{
                            "type": "text",
                            "text": _system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }],
                        messages=_api_messages,
                    ) as stream:
                        thinking.empty()
                        response_text = st.write_stream(stream.text_stream)

            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": response_text,
            })

        except anthropic.AuthenticationError:
            st.error("API 키가 유효하지 않습니다.")
        except anthropic.RateLimitError:
            st.error("API 사용량 한도를 초과했습니다. 잠시 후 다시 시도하세요.")
        except Exception as e:
            st.error(f"AI 응답 오류: {e}")
