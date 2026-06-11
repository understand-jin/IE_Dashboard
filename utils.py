import os
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
import requests
from datetime import timedelta
import calendar
from functools import lru_cache
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_RATE_CACHE_PATH = "Output_data/exchange_rate_cache.json"

def _load_rate_cache() -> dict:
    try:
        with open(_RATE_CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_rate_cache(cache: dict):
    os.makedirs("Output_data", exist_ok=True)
    with open(_RATE_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

@lru_cache(maxsize=128)
def get_exchange_rate(date_str: str, currency: str) -> float:
    """날짜 문자열(YYYYMMDD) 기준 환율 조회. 파일 캐시 → API 순서로 조회."""
    cache_key = f"{date_str}_{currency}"

    # 1) 파일 캐시 확인
    cache = _load_rate_cache()
    if cache_key in cache:
        print(f"[환율 캐시 HIT] {cache_key} = {cache[cache_key]}")
        return cache[cache_key]

    # 2) API 호출
    API_KEY = "K2b7PPzKBuW7SdlgyRV6Y4c8nuH0nlDn"
    base = pd.Timestamp(date_str)
    for i in range(10):
        target = base - pd.Timedelta(days=i)
        url = "https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON"
        params = {"authkey": API_KEY, "searchdate": target.strftime("%Y%m%d"), "data": "AP01"}
        try:
            res = requests.get(url, params=params, verify=False, timeout=10)
            data = res.json()
        except Exception:
            continue
        if not data:
            continue
        # result:4 = 일일 한도 초과
        if isinstance(data, list) and data and data[0].get("result") == 4:
            print(f"[환율 API] 일일 한도 초과 — 캐시된 값 없음: {cache_key}")
            return None
        for item in data:
            if item.get("cur_unit") == currency and item.get("deal_bas_r"):
                rate = float(item["deal_bas_r"].replace(",", ""))
                # 3) 성공 시 파일 캐시에 저장
                cache[cache_key] = rate
                _save_rate_cache(cache)
                print(f"[환율 API 조회 성공] {cache_key} = {rate}")
                return rate
    return None


def fill_krw_amount(df: pd.DataFrame, base_date: pd.Timestamp) -> pd.DataFrame:
    df["입고금액(현지통화)"] = pd.to_numeric(df["입고금액(현지통화)"], errors="coerce").astype(float)
    df["금액"] = pd.to_numeric(df["금액"], errors="coerce").astype(float)
    df["통화"] = df["통화"].astype(str).str.upper().str.strip()

    date_key = base_date.strftime("%Y%m%d")
    currency_map = {
        "USD": ("USD",     get_exchange_rate(date_key, "USD")),
        "JPY": ("JPY(100)", get_exchange_rate(date_key, "JPY(100)")),
        "EUR": ("EUR",     get_exchange_rate(date_key, "EUR")),
    }

    print(f"[{base_date.strftime('%Y-%m-%d')} 기준 환율]")
    for cur, (api_key, rate) in currency_map.items():
        print(f"  {cur}: {rate}")

    FALLBACK_RATES = {"USD": 1500, "JPY": 900, "EUR": 1700}

    for cur, (api_key, rate) in currency_map.items():
        if rate is None:
            rate = FALLBACK_RATES[cur]
            print(f"  {cur} 환율 조회 실패 - 기본값 사용: {rate}")

        actual_rate = rate / 100 if cur == "JPY" else rate

        mask = (
            (df["입고금액(현지통화)"].isna() | (df["입고금액(현지통화)"] == 0)) &
            (df["통화"] == cur)
        )
        df.loc[mask, "입고금액(현지통화)"] = df.loc[mask, "금액"] * actual_rate

    return df


def standard_data_processing():
    path = "Input_data/ZMMR0210/ZMMR0210.xlsx"
    df = pd.read_excel(path, engine="openpyxl")
    df = df[["구매오더", "회사코드", "구매오더품번", "자재", "자재내역", "자재유형", "자재그룹",
              "오더수량", "오더단위", "금액", "통화", "납품일", "납품상태", "플랜트",
              "입고일", "입고수량", "입고금액(현지통화)"]]

    df["회사코드"] = df["회사코드"].astype(int)
    dw_df  = df[df["회사코드"] == 1200].reset_index(drop=True)
    dwb_df = df[df["회사코드"] == 1300].reset_index(drop=True)

    path_DW_M = "Input_data/대웅제약_품목유형/대웅제약_품목유형.xlsx"
    master_dw = pd.read_excel(path_DW_M, engine="openpyxl")
    master_dw["자재"] = master_dw["자재"].astype(int)
    master_dw["제품군"] = master_dw["제품군"].astype(str)
    master_dw["품목유형"] = master_dw["품목유형"].astype(str)
    dw_df["자재"] = dw_df["자재"].astype(int)
    dw_df = dw_df.merge(master_dw[["자재", "제품군", "품목유형"]], on="자재", how="left")

    dw_df["자재내역"] = dw_df["자재내역"].astype(str)
    opadry_mask = (
        (dw_df["품목유형"].isna() | (dw_df["품목유형"] == "비라이선스")) &
        dw_df["자재내역"].str.contains("Opadry|오파드라이|OPADRY|Colorcon", case=False, na=False)
    )
    dw_df.loc[opadry_mask, "품목유형"] = "오파드라이"
    dw_df.loc[opadry_mask, "제품군"]   = "오파드라이"

    dwb_df["자재내역"] = dwb_df["자재내역"].astype(str)
    dwb_df["품목유형"] = "일반"
    keyword_map = {
        "UDCA": ["CDCA", "UDCA", "CA"],
        "콜린": ["Choline"],
        "펙수": ["PC", "FBSC", "BAIB", "TEMPO"],
        "세파": ["Cefa", "Cefu", "Cef"],
    }
    for type_name, keywords in keyword_map.items():
        pattern = "|".join(keywords)
        mask = dwb_df["자재내역"].str.contains(pattern, case=False, na=False)
        dwb_df.loc[mask, "품목유형"] = type_name

    dw_df["납품일"]  = pd.to_datetime(dw_df["납품일"])
    dwb_df["납품일"] = pd.to_datetime(dwb_df["납품일"])

    today = pd.Timestamp.today().normalize()

    m0_start = today.replace(day=1)
    m0_end   = today
    m1_start = (today - pd.DateOffset(months=1)).replace(day=1)
    m1_end   = m0_start - pd.Timedelta(days=1)
    m2_start = (today - pd.DateOffset(months=2)).replace(day=1)
    m2_end   = m1_start - pd.Timedelta(days=1)
    m3_start = (today - pd.DateOffset(months=3)).replace(day=1)
    m3_end   = m2_start - pd.Timedelta(days=1)

    def split_by_month(src, start, end):
        d = src["납품일"]
        return src[(d >= start) & (d <= end)].reset_index(drop=True)

    m0_dw = split_by_month(dw_df,  m0_start, m0_end)
    m1_dw = split_by_month(dw_df,  m1_start, m1_end)
    m2_dw = split_by_month(dw_df,  m2_start, m2_end)
    m3_dw = split_by_month(dw_df,  m3_start, m3_end)

    m0_dwb = split_by_month(dwb_df, m0_start, m0_end)
    m1_dwb = split_by_month(dwb_df, m1_start, m1_end)
    m2_dwb = split_by_month(dwb_df, m2_start, m2_end)
    m3_dwb = split_by_month(dwb_df, m3_start, m3_end)

    m0_dw  = fill_krw_amount(m0_dw,  m0_end)
    m1_dw  = fill_krw_amount(m1_dw,  m1_end)
    m2_dw  = fill_krw_amount(m2_dw,  m2_end)
    m3_dw  = fill_krw_amount(m3_dw,  m3_end)

    m0_dwb = fill_krw_amount(m0_dwb, m0_end)
    m1_dwb = fill_krw_amount(m1_dwb, m1_end)
    m2_dwb = fill_krw_amount(m2_dwb, m2_end)
    m3_dwb = fill_krw_amount(m3_dwb, m3_end)

    final_df = pd.concat(
        [m0_dw, m1_dw, m2_dw, m3_dw, m0_dwb, m1_dwb, m2_dwb, m3_dwb],
        ignore_index=True,
    )

    # 반환 순서: 당월, 전월, 전전월, 전전전월 (DW/DWB) + final_df
    return (
        m0_dw, m1_dw, m2_dw, m3_dw,
        m0_dwb, m1_dwb, m2_dwb, m3_dwb,
        dw_df, final_df,
    )


def _rate_str(src_df: pd.DataFrame, col: str = None, val: str = None) -> str:
    """납기준수율 계산. val=None이면 전체 합산."""
    if src_df is None or len(src_df) == 0:
        return "-"
    sub = src_df[src_df[col] == val] if val is not None else src_df
    total = len(sub)
    if total == 0:
        return "-"
    done = len(sub[sub["납품상태"] == "정상"])
    return f"{done / total:.1%}"


def make_dw_summary(
    df: pd.DataFrame,
    label: str,
    prev2_df: pd.DataFrame = None,
    prev2_label: str = None,
    prev3_df: pd.DataFrame = None,
    prev3_label: str = None,
    target_rate: float = 0.80,
) -> pd.DataFrame:
    """대웅제약 품목유형별 건수/금액/납기준수율 요약표 (3개월 추세 + 목표)"""

    types = ["상품", "반제", "라이선스", "비라이선스", "오파드라이"]
    col_3m = f"납기준수율({prev3_label})" if prev3_label else None
    col_2m = f"납기준수율({prev2_label})" if prev2_label else None
    col_1m = f"납기준수율({label})"

    rows = []
    for t in types:
        sub = df[df["품목유형"] == t]
        total_cnt = len(sub)
        total_amt = sub["입고금액(현지통화)"].sum()
        done_cnt  = len(sub[sub["납품상태"] == "정상"])
        done_amt  = sub[sub["납품상태"] == "정상"]["입고금액(현지통화)"].sum()

        row = {
            "구분": t,
            "전체건수": total_cnt,
            "전체금액(억)": round(total_amt / 1e8, 1),
            "완료건수": done_cnt,
            "완료금액(억)": round(done_amt / 1e8, 1),
        }
        if col_3m:
            row[col_3m] = _rate_str(prev3_df, "품목유형", t)
        if col_2m:
            row[col_2m] = _rate_str(prev2_df, "품목유형", t)
        row[col_1m] = f"{done_cnt / total_cnt:.1%}" if total_cnt > 0 else "-"
        row["목표"]  = f"{target_rate:.1%}"
        rows.append(row)

    result = pd.DataFrame(rows)

    total_cnt_sum = result["전체건수"].sum()
    done_cnt_sum  = result["완료건수"].sum()
    subtotal = {
        "구분": f"대웅제약 소계 ({label})",
        "전체건수": total_cnt_sum,
        "전체금액(억)": round(result["전체금액(억)"].sum(), 1),
        "완료건수": done_cnt_sum,
        "완료금액(억)": round(result["완료금액(억)"].sum(), 1),
    }
    if col_3m:
        subtotal[col_3m] = _rate_str(prev3_df)
    if col_2m:
        subtotal[col_2m] = _rate_str(prev2_df)
    subtotal[col_1m] = f"{done_cnt_sum / total_cnt_sum:.1%}" if total_cnt_sum > 0 else "0.0%"
    subtotal["목표"] = f"{target_rate:.1%}"

    return pd.concat([pd.DataFrame([subtotal]), result], ignore_index=True)


def make_dwb_summary(
    df: pd.DataFrame,
    label: str,
    prev2_df: pd.DataFrame = None,
    prev2_label: str = None,
    prev3_df: pd.DataFrame = None,
    prev3_label: str = None,
    target_rate: float = 0.80,
) -> pd.DataFrame:
    """대웅바이오 품목유형별 건수/금액/납기준수율 요약표 (3개월 추세 + 목표)"""

    types = ["일반", "UDCA", "콜린", "펙수", "세파"]
    col_3m = f"납기준수율({prev3_label})" if prev3_label else None
    col_2m = f"납기준수율({prev2_label})" if prev2_label else None
    col_1m = f"납기준수율({label})"

    rows = []
    for t in types:
        sub = df[df["품목유형"] == t]
        total_cnt = len(sub)
        total_amt = sub["입고금액(현지통화)"].sum()
        done_cnt  = len(sub[sub["납품상태"] == "정상"])
        done_amt  = sub[sub["납품상태"] == "정상"]["입고금액(현지통화)"].sum()

        row = {
            "구분": t,
            "전체건수": total_cnt,
            "전체금액(억)": round(total_amt / 1e8, 1),
            "완료건수": done_cnt,
            "완료금액(억)": round(done_amt / 1e8, 1),
        }
        if col_3m:
            row[col_3m] = _rate_str(prev3_df, "품목유형", t)
        if col_2m:
            row[col_2m] = _rate_str(prev2_df, "품목유형", t)
        row[col_1m] = f"{done_cnt / total_cnt:.1%}" if total_cnt > 0 else "-"
        row["목표"]  = f"{target_rate:.1%}"
        rows.append(row)

    result = pd.DataFrame(rows)

    total_cnt_sum = result["전체건수"].sum()
    done_cnt_sum  = result["완료건수"].sum()
    subtotal = {
        "구분": f"대웅바이오 소계 ({label})",
        "전체건수": total_cnt_sum,
        "전체금액(억)": round(result["전체금액(억)"].sum(), 1),
        "완료건수": done_cnt_sum,
        "완료금액(억)": round(result["완료금액(억)"].sum(), 1),
    }
    if col_3m:
        subtotal[col_3m] = _rate_str(prev3_df)
    if col_2m:
        subtotal[col_2m] = _rate_str(prev2_df)
    subtotal[col_1m] = f"{done_cnt_sum / total_cnt_sum:.1%}" if total_cnt_sum > 0 else "0.0%"
    subtotal["목표"] = f"{target_rate:.1%}"

    return pd.concat([pd.DataFrame([subtotal]), result], ignore_index=True)
