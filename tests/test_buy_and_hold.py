
import time
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가합니다.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from workers.tasks import run_backtest_task
from dotenv import load_dotenv

# .env 파일 로드
# 프로젝트 루트에 있는 .env 파일을 로드하도록 경로 수정
load_dotenv(dotenv_path=os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'workers', '.env'))

# 백테스트할 전략의 파라미터를 정의합니다.
strategy_params = {
    'asset_weights': [
        {'asset': 'SPY', 'weight': 0.6},
        {'asset': 'AGG', 'weight': 0.4}
    ] # 예: 60/40 포트폴리오
}

# Celery를 통하지 않고 백테스트 로직을 직접 실행합니다.
print("백테스트 로직을 직접 실행합니다...")
try:
    results = run_backtest_task(
        strategy_name='BuyAndHoldStrategy', # BuyAndHoldStrategy를 직접 지정
        strategy_params=strategy_params,
        initial_capital=100000000.0,
        start_date='2016-01-04',
        end_date='2020-12-30',
        debug=True # 디버그 로깅 활성화
    )

    print("\n--- 백테스트 결과 수신 (직접 실행) ---")
    if 'error' in results:
        print(f"오류 발생: {results['error']}")
    else:
        # 전체 결과를 출력하면 너무 길어지므로, 주요 성과 지표만 출력합니다.
        perf = results.get('performance_metrics', {})
        print("주요 성과 지표:")
        print(f"  - 최종 수익률: {perf.get('total_return', 0) * 100:.2f}%")
        print(f"  - 연환산 수익률: {perf.get('annualized_return', 0) * 100:.2f}%")
        print(f"  - 변동성: {perf.get('volatility', 0) * 100:.2f}%")
        print(f"  - 샤프 지수: {perf.get('sharpe_ratio', 0):.2f}")
        print(f"  - 최대 낙폭(MDD): {perf.get('max_drawdown', 0) * 100:.2f}%")
        print(f"\n총 {len(results.get('transactions', []))} 건의 거래가 발생했습니다.")

except Exception as e:
    print(f"\n백테스트 로직 직접 실행 중 오류가 발생했습니다: {e}")
