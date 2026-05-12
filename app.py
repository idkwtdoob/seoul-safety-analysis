# --- 1. 페이지 설정 ---
st.set_page_config(page_title="서울시 생활안전 대시보드", layout="wide")

# --- 2. DB 연결 및 분석용 테이블 생성 ---
DB_FILE = "1인가구.db"
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="서울시 생활안전 대시보드", layout="wide")

# --- 2. DB 연결 및 분석용 테이블 생성 (기존 로직 동일) ---
DB_FILE = "seoul_safety.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

if not os.path.exists(DB_FILE):
    st.error(f"❌ '{DB_FILE}' 파일이 없습니다. 폴더에 데이터베이스 파일을 넣어주세요.")
    st.stop()

@st.cache_data
def init_database():
    conn = get_connection()
    cursor = conn.cursor()
    
    # [SQL 1] 1인가구_연령층 생성
    cursor.execute("DROP TABLE IF EXISTS \"1인가구_연령층\";")
    cursor.execute("""
    CREATE TABLE "1인가구_연령층" AS
    SELECT "연도", "자치구", "성별", "연령",
        CASE
            WHEN "연령" IN ('20세미만', '20~24세', '25~29세', '30~34세') THEN '청년층'
            WHEN "연령" IN ('35~39세', '40~44세', '45~49세', '50~54세', '55~59세', '60~64세') THEN '중장년층'
            WHEN "연령" IN ('65~69세', '70~74세', '75~79세', '80~84세', '85세이상') THEN '고령층'
            ELSE '기타'
        END AS "연령층",
        "1인가구수"
    FROM "1인가구";
    """)

    # [SQL 2] 1인가구_자치구요약 생성
    cursor.execute("DROP TABLE IF EXISTS \"1인가구_자치구요약\";")
    cursor.execute("""
    CREATE TABLE "1인가구_자치구요약" AS
    SELECT "자치구", SUM("1인가구수") AS "전체_1인가구수",
        SUM(CASE WHEN "연령층" = '청년층' THEN "1인가구수" ELSE 0 END) AS "청년층_1인가구수",
        SUM(CASE WHEN "연령층" = '중장년층' THEN "1인가구수" ELSE 0 END) AS "중장년층_1인가구수",
        SUM(CASE WHEN "연령층" = '고령층' THEN "1인가구수" ELSE 0 END) AS "고령층_1인가구수",
        ROUND(SUM(CASE WHEN "연령층" = '청년층' THEN "1인가구수" ELSE 0 END) * 100.0 / SUM("1인가구수"), 2) AS "청년층_비중",
        ROUND(SUM(CASE WHEN "연령층" = '고령층' THEN "1인가구수" ELSE 0 END) * 100.0 / SUM("1인가구수"), 2) AS "고령층_비중"
    FROM "1인가구_연령층" GROUP BY "자치구";
    """)

    # [SQL 3] 안전서비스_자치구요약 생성
    cursor.execute("DROP TABLE IF EXISTS \"안전서비스_자치구요약\";")
    cursor.execute("""
    CREATE TABLE "안전서비스_자치구요약" AS
    SELECT h."자치구",
        COALESCE(b."안심택배함수", 0) AS "안심택배함수",
        COALESCE(r."안심귀갓길_지점수", 0) AS "안심귀갓길_지점수",
        COALESCE(r."안심귀갓길_노선수", 0) AS "안심귀갓길_노선수",
        COALESCE(s."이용실적", 0) AS "스카우트_이용실적",
        COALESCE(s."스카우트 인원", 0) AS "스카우트_인원"
    FROM "1인가구_자치구요약" h
    LEFT JOIN (SELECT "자치구", COUNT(*) AS "안심택배함수" FROM "안심택배함" GROUP BY "자치구") b ON h."자치구" = b."자치구"
    LEFT JOIN (SELECT "자치구", COUNT(*) AS "안심귀갓길_지점수", COUNT(DISTINCT "안심귀갓길 id") AS "안심귀갓길_노선수" FROM "안심귀갓길서비스" GROUP BY "자치구") r ON h."자치구" = r."자치구"
    LEFT JOIN "안심귀가스카우트이용현황" s ON h."자치구" = s."자치구";
    """)

    # [SQL 4] 분석용_자치구 생성
    cursor.execute("DROP TABLE IF EXISTS \"분석용_자치구\";")
    cursor.execute("""
    CREATE TABLE "분석용_자치구" AS
    SELECT h."자치구", h."전체_1인가구수", h."청년층_1인가구수", h."중장년층_1인가구수", h."고령층_1인가구수", h."청년층_비중", h."고령층_비중",
        s."안심택배함수", s."안심귀갓길_지점수", s."안심귀갓길_노선수", s."스카우트_이용실적", s."스카우트_인원",
        ROUND(s."안심택배함수" * 10000.0 / h."전체_1인가구수", 2) AS "1만명당_안심택배함수",
        ROUND(s."안심귀갓길_지점수" * 10000.0 / h."전체_1인가구수", 2) AS "1만명당_안심귀갓길지점수",
        ROUND(s."스카우트_이용실적" * 10000.0 / h."전체_1인가구수", 2) AS "1만명당_스카우트이용실적",
        ROUND(s."스카우트_이용실적" * 1.0 / NULLIF(s."스카우트_인원", 0), 2) AS "스카우트1명당_이용실적"
    FROM "1인가구_자치구요약" h
    LEFT JOIN "안전서비스_자치구요약" s ON h."자치구" = s."자치구";
    """)
    conn.commit()
    conn.close()

init_database()

def run_query(q):
    with get_connection() as conn:
        return pd.read_sql(q, conn)

# --- 상단 타이틀 및 KPI 섹션 ---
st.title("📊 2024 서울시 1인가구 생활안전 서비스 분석 대시보드")
st.markdown("2024년 기준 서울시 자치구별 1인가구 분포와 생활안전 서비스 인프라를 한눈에 비교합니다.")

total_stats = run_query("""
    SELECT SUM(전체_1인가구수) as hh, SUM(안심택배함수) as box, 
           SUM(안심귀갓길_지점수) as road, SUM(스카우트_이용실적) as scout 
    FROM 분석용_자치구
""").iloc[0]

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("2024 서울시 전체 1인가구", f"{int(total_stats['hh']):,}명")
kpi2.metric("총 안심택배함", f"{int(total_stats['box']):,}개")
kpi3.metric("총 안심귀갓길 지점", f"{int(total_stats['road']):,}곳")
kpi4.metric("총 스카우트 이용실적", f"{int(total_stats['scout']):,}건")

# --- [추가] 분석용 테이블 생성 SQL 토글 섹션 ---
with st.expander("*분석용 테이블 생성 SQL 코드 자세히 보기*"):
    st.markdown("""
    본 분석에서는 기존의 세분화된 연령대(예: 20\~24세, 25\~29세 등)를 **청년층, 중장년층, 고령층**으로 재분류하여 
    분석의 가독성을 높이고 자치구별 인프라 수요를 보다 명확히 파악하고자 분석용 테이블을 별도로 생성하였습니다.
    """)
    
    # 콜아웃 박스 1
    st.info("1. 연령대 재분류 (1인가구_연령층)")
    st.code("""
DROP TABLE IF EXISTS "1인가구_연령층";
CREATE TABLE "1인가구_연령층" AS
SELECT "연도", "자치구", "성별", "연령",
    CASE
        WHEN "연령" IN ('20세미만', '20~24세', '25~29세', '30~34세') THEN '청년층'
        WHEN "연령" IN ('35~39세', '40~44세', '45~49세', '50~54세', '55~59세', '60~64세') THEN '중장년층'
        WHEN "연령" IN ('65~69세', '70~74세', '75~79세', '80~84세', '85세이상') THEN '고령층'
        ELSE '기타'
    END AS "연령층",
    "1인가구수"
FROM "1인가구";
    """, language="sql")

    # 콜아웃 박스 2
    st.info("2. 자치구별 연령층 요약 (1인가구_자치구요약)")
    st.code("""
DROP TABLE IF EXISTS "1인가구_자치구요약";
CREATE TABLE "1인가구_자치구요약" AS
SELECT "자치구", SUM("1인가구수") AS "전체_1인가구수",
    SUM(CASE WHEN "연령층" = '청년층' THEN "1인가구수" ELSE 0 END) AS "청년층_1인가구수",
    SUM(CASE WHEN "연령층" = '중장년층' THEN "1인가구수" ELSE 0 END) AS "중장년층_1인가구수",
    SUM(CASE WHEN "연령층" = '고령층' THEN "1인가구수" ELSE 0 END) AS "고령층_1인가구수",
    ROUND(SUM(CASE WHEN "연령층" = '청년층' THEN "1인가구수" ELSE 0 END) * 100.0 / SUM("1인가구수"), 2) AS "청년층_비중",
    ROUND(SUM(CASE WHEN "연령층" = '고령층' THEN "1인가구수" ELSE 0 END) * 100.0 / SUM("1인가구수"), 2) AS "고령층_비중"
FROM "1인가구_연령층" GROUP BY "자치구";
    """, language="sql")

    # 콜아웃 박스 3
    st.info("3. 안전 서비스 데이터 집계 (안전서비스_자치구요약)")
    st.code("""
DROP TABLE IF EXISTS "안전서비스_자치구요약";
CREATE TABLE "안전서비스_자치구요약" AS
SELECT h."자치구",
    COALESCE(b."안심택배함수", 0) AS "안심택배함수",
    COALESCE(r."안심귀갓길_지점수", 0) AS "안심귀갓길_지점수",
    COALESCE(r."안심귀갓길_노선수", 0) AS "안심귀갓길_노선수",
    COALESCE(s."이용실적", 0) AS "스카우트_이용실적",
    COALESCE(s."스카우트 인원", 0) AS "스카우트_인원"
FROM "1인가구_자치구요약" h
LEFT JOIN (SELECT "자치구", COUNT(*) AS "안심택배함수" FROM "안심택배함" GROUP BY "자치구") b ON h."자치구" = b."자치구"
LEFT JOIN (SELECT "자치구", COUNT(*) AS "안심귀갓길_지점수", COUNT(DISTINCT "안심귀갓길 id") AS "안심귀갓길_노선수" FROM "안심귀갓길서비스" GROUP BY "자치구") r ON h."자치구" = r."자치구"
LEFT JOIN "안심귀가스카우트이용현황" s ON h."자치구" = s."자치구";
    """, language="sql")

    # 콜아웃 박스 4
    st.info("4. 최종 분석용 데이터 결합 및 파생 지표 생성 (분석용_자치구)")
    st.code("""
DROP TABLE IF EXISTS "분석용_자치구";
CREATE TABLE "분석용_자치구" AS
SELECT h."자치구", h."전체_1인가구수", h."청년층_1인가구수", h."중장년층_1인가구수", h."고령층_1인가구수", h."청년층_비중", h."고령층_비중",
    s."안심택배함수", s."안심귀갓길_지점수", s."안심귀갓길_노선수", s."스카우트_이용실적", s."스카우트_인원",
    ROUND(s."안심택배함수" * 10000.0 / h."전체_1인가구수", 2) AS "1만명당_안심택배함수",
    ROUND(s."안심귀갓길_지점수" * 10000.0 / h."전체_1인가구수", 2) AS "1만명당_안심귀갓길지점수",
    ROUND(s."스카우트_이용실적" * 10000.0 / h."전체_1인가구수", 2) AS "1만명당_스카우트이용실적",
    ROUND(s."스카우트_이용실적" * 1.0 / NULLIF(s."스카우트_인원", 0), 2) AS "스카우트1명당_이용실적"
FROM "1인가구_자치구요약" h
LEFT JOIN "안전서비스_자치구요약" s ON h."자치구" = s."자치구";
    """, language="sql")

st.divider()

# --- 차트 1: 안심택배함 ---
st.header("1. 1인가구 밀집지역의 안심택배함 설치 충분성")
sql1 = """
SELECT "자치구", "전체_1인가구수", "안심택배함수", "1만명당_안심택배함수"
FROM "분석용_자치구"
ORDER BY "1만명당_안심택배함수" ASC;
"""
df1 = run_query(sql1)
fig1 = px.bar(df1, x="1만명당_안심택배함수", y="자치구", orientation='h', 
             color="1만명당_안심택배함수", color_continuous_scale="Reds")
st.plotly_chart(fig1, use_container_width=True)

st.subheader("📝 사용된 SQL")
st.code(sql1, language="sql")

st.subheader("💡 인사이트")
st.markdown("""
- 안심택배함은 단순 설치 개수보다 1인가구 수 대비 공급량으로 비교했을 때 지역 간 격차가 뚜렷하게 나타남.
- 일부 자치구에서는 1인가구 규모에 비해 안심택배함 접근성이 상대적으로 낮을 수 있음.
""")

st.divider()

# --- 차트 2: 안심귀갓길 vs 스카우트 ---
st.header("2. 안심귀갓길 인프라와 실제 이용 수요의 균형")

# 친절하고 이해하기 쉬운 그래프 가이드 추가
st.info("""
**💡 이 그래프를 사분면으로 나누어 분석해볼까요?**
중앙의 두 점선(평균선)을 기준으로 자치구가 어느 위치에 있는지 확인해보세요!

1. **좌측 상단 (수요 높음 🚨, 인프라 낮음):** 이용 실적은 평균보다 높지만 인프라는 부족한 곳입니다. **가장 먼저 서비스를 확충해야 할 지역**입니다.
2. **우측 상단 (수요 높음 ✅, 인프라 높음):** 서비스 이용이 활발하고 인프라도 잘 갖춰진 **모범 자치구**들입니다.
3. **우측 하단 (수요 낮음 🤔, 인프라 높음):** 인프라는 많지만 이용이 적은 곳입니다. 서비스 홍보를 강화하거나 효율적인 재배치가 필요할 수 있습니다.
4. **좌측 하단 (수요 낮음 🔍, 인프라 낮음):** 수요와 인프라가 모두 평균 이하인 지역으로, 향후 변화를 관찰할 필요가 있습니다.

- **점의 크기:** 해당 구의 **전체 1인가구 수**가 많을수록 점이 커집니다.
- **점의 색상:** **청년층 비중**이 높을수록 진한 파란색을 띱니다.
""")

sql2 = """
SELECT "자치구", "1만명당_안심귀갓길지점수", "1만명당_스카우트이용실적", "청년층_비중", "전체_1인가구수"
FROM "분석용_자치구";
"""
df2 = run_query(sql2)

# 시각화 설정 (hover_name에 자치구를 넣어 마우스를 올리면 이름을 볼 수 있게 함)
fig2 = px.scatter(df2, 
                 x="1만명당_안심귀갓길지점수", 
                 y="1만명당_스카우트이용실적", 
                 size="전체_1인가구수", 
                 color="청년층_비중", 
                 hover_name="자치구",
                 labels={
                     "1만명당_안심귀갓길지점수": "1만명당 안심귀갓길 지점수 (공급)",
                     "1만명당_스카우트이용실적": "1만명당 스카우트 이용실적 (수요)"
                 },
                 color_continuous_scale="Blues")

# 평균선 및 텍스트 추가
fig2.add_hline(y=df2["1만명당_스카우트이용실적"].mean(), line_dash="dot", annotation_text="실적 평균")
fig2.add_vline(x=df2["1만명당_안심귀갓길지점수"].mean(), line_dash="dot", annotation_text="인프라 평균")

st.plotly_chart(fig2, use_container_width=True)

st.subheader("📝 사용된 SQL")
st.code(sql2, language="sql")

st.subheader("💡 인사이트")
st.markdown(f"""
- 평균 실적선보다 한참 위로 솟아 있는 점들은 해당 구의 1인가구들이 생활안전 서비스를 매우 적극적으로 활용하고 있음을 나타냄.
- **특히 좌상단 영역(🚨)**에 위치한 자치구는 이용 수요에 비해 물리적인 귀갓길 지점 수가 부족하므로, 우선적인 행정 지원이 검토되어야 함.
- 점의 크기가 가장 큰 자치구(1인가구 밀집 지역)인 관악구가 4사분면에 위치하므로 향후 관찰 필요.
""")

st.divider()

# --- 차트 3: 확충 우선순위 ---
st.header("3. 생활안전 서비스 확충 우선순위 TOP 10")

# 1. 점수 계산 로직 설명 (사용자 이해 돕기)
st.success("""
**💡 우선순위 점수는 어떻게 계산되나요?**
이 점수는 다음 4가지 항목의 **자치구별 순위**를 합산한 결과입니다.
1. **1인가구 수**가 많을수록 (수요가 높음) → 1등에 가까움
2. **1만명당 스카우트 이용실적**이 높을수록 (활용도가 높음) → 1등에 가까움
3. **1만명당 안심택배함수**가 적을수록 (공급이 부족함) → 1등에 가까움
4. **1만명당 안심귀갓길지점수**가 적을수록 (공급이 부족함) → 1등에 가까움

**결과적으로, 네 항목의 순위를 더한 '우선순위 점수'가 낮을수록(숫자가 작을수록) 개선이 가장 시급한 지역을 의미합니다.**
""")

sql4 = """
SELECT "자치구", 
       RANK() OVER (ORDER BY "전체_1인가구수" DESC) +
       RANK() OVER (ORDER BY "1만명당_스카우트이용실적" DESC) +
       RANK() OVER (ORDER BY "1만명당_안심택배함수" ASC) +
       RANK() OVER (ORDER BY "1만명당_안심귀갓길지점수" ASC) as "우선순위점수"
FROM "분석용_자치구"
ORDER BY "우선순위점수" ASC  -- 점수 낮은 순으로 10개 추출
LIMIT 10;
"""
df4 = run_query(sql4)

# 시각화 수정: 가장 시급한(점수 낮은) 자치구가 맨 위로 오도록 데이터프레임 역순 정렬
# Plotly의 가로 막대 차트는 데이터프레임의 마지막 행을 맨 위에 그리는 특성이 있습니다.
df4_plot = df4.sort_values(by="우선순위점수", ascending=False)

fig4 = px.bar(df4_plot, 
             x="우선순위점수", 
             y="자치구", 
             orientation='h', 
             title="자치구별 서비스 개선 시급성 (점수가 낮을수록 최우선순위)",
             color="우선순위점수", 
             color_continuous_scale="Viridis") # 낮은 점수가 눈에 띄도록 색상 변경

# 막대 옆에 실제 점수 표시
fig4.update_traces(texttemplate='%{x}점', textposition='outside')

st.plotly_chart(fig4, use_container_width=True)

st.subheader("📝 사용된 SQL")
st.code(sql4, language="sql")

st.subheader("💡 인사이트")
st.markdown(f"""
- **{df4.iloc[0]['자치구']}** 지역이 우선순위 점수 **{df4.iloc[0]['우선순위점수']}점**으로 서울시에서 가장 개선이 시급한 지역 TOP 10 중 1위로 나타남.
- 상위권에 속한 자치구들은 공통적으로 1인가구 수요에 비해 물리적인 안심 인프라(택배함, 귀갓길)가 상대적으로 부족한 상태.
- **개선 우선순위(심각성):** { " > ".join(df4['자치구'].tolist()) } 순.
""")

