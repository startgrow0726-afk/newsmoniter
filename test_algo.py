import os
import sys

# 프로젝트 루트를 Python 경로에 추가하여 모듈 임포트 가능하게 함
# 이 스크립트가 프로젝트 루트에 있다고 가정합니다.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api'))

# server.py에서 필요한 함수 임포트
# server.py에 있는 함수들은 직접 임포트할 수 있습니다.
from server import summarize_en, detect_category, sentiment_score, detect_companies_from_db, load_company_db

def run_custom_algo_tests():
    print("--- Custom Algorithm Tests ---")

    # 1. 요약 알고리즘 테스트
    text_to_summarize = """
    Tesla's stock price surged recently after news of CEO Elon Musk's large-scale share purchases. Musk acquired approximately 2.5 million shares (worth about $1 billion), marking his first major open market purchase in 5 years and 7 months, demonstrating confidence in the company to investors. Following this news, Tesla's stock rose by about 20% over 7 of the last 8 trading days, increasing its market capitalization by $230 billion. On September 15 (local time), it closed at $410.04, up 3.56% from the previous day. Wall Street analysts are also raising their price targets, focusing on Tesla's future growth drivers.
    """
    summary = summarize_en(text_to_summarize, max_sentences=2)
    print(f"\nOriginal Text:\n{text_to_summarize}")
    print(f"Summary (2 sentences):\n{summary}")

    # 2. 카테고리 감지 알고리즘 테스트
    category = detect_category(text_to_summarize)
    print(f"\nDetected Category: {category}")

    # 3. 감성 분석 알고리즘 테스트
    sentiment = sentiment_score(text_to_summarize)
    print(f"Sentiment Score: {sentiment}") # -1.0 (부정) ~ 1.0 (긍정)

    # 4. 회사 매칭 알고리즘 테스트
    # detect_companies_from_db를 사용하려면 company_db가 필요합니다.
    # server.py의 load_company_db 함수를 사용합니다.
    company_db = load_company_db()
    if company_db:
        title = "Tesla Stock Surges on News of Musk's Share Purchases"
        body = text_to_summarize
        matched_companies = detect_companies_from_db(title, body, company_db)
        print(f"\nMatched Companies for '{title}': {matched_companies}")
        for company in matched_companies:
            print(f"  - {company['name']} (Confidence: {company['confidence']})")

        # 5. Tesla 직접 매칭 테스트
        print("\n--- Direct Tesla Matching Test ---")
        tesla_title = "Tesla (TSLA) stock rises on new EV model announcement"
        tesla_body = "Elon Musk confirmed that Tesla will launch a new affordable electric vehicle next year."
        matched_tesla = detect_companies_from_db(tesla_title, tesla_body, company_db)
        print(f"Matched Companies for '{tesla_title}': {matched_tesla}")
        if matched_tesla and any(c['name'] == 'Tesla' for c in matched_tesla):
            print("PASS: Tesla successfully matched.")
        else:
            print("FAIL: Tesla not matched.")
    else:
        print("\n회사 DB를 로드할 수 없어 회사 매칭 테스트를 건너뛰었습니다. 'data/companies_context.json' 파일이 있는지 확인하세요.")


if __name__ == "__main__":
    # server.py의 함수들이 환경 변수에 의존할 수 있으므로, 필요하다면 설정합니다.
    os.environ['MIN_CONFIDENCE_DISPLAY'] = '0.0' # 테스트를 위해 임시로 낮춤
    run_custom_algo_tests()
