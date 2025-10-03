
import time
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가합니다.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from workers.tasks import run_backtest_task
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# 백테스트할 모멘텀 전략의 파라미터를 정의합니다.
strategy_params = {
    'asset_pool': ['SPY', 'EFA', 'AGG'], # 자산군: 미국 주식, 선진국 주식, 미국 채권
    'lookback_period_months': 6,          # 모멘텀 계산 기간: 6개월
    'top_n_assets': 1,                     # 선택할 상위 자산 수: 1개
    'risk_free_asset_ticker': 'DGS1'       # 무위험 자산: 미국 1년 만기 국채
}

print("모멘텀 전략 백테스트 작업을 Celery 워커에게 요청합니다...")
task = run_backtest_task.delay(
    strategy_name='MomentumStrategy', 
    strategy_params=strategy_params,
    start_date='2022-01-01', 
    end_date='2022-12-31'
)

print(f"작업이 성공적으로 전달되었습니다. Task ID: {task.id}")
print("결과를 기다리는 중... (최대 60초)")

try:
    result = task.get(timeout=120)

    print("\n--- 백테스트 결과 수신 ---")
    if 'error' in result:
        print(f"오류 발생: {result['error']}")
    else:
        perf = result.get('performance_metrics', {})
        print("주요 성과 지표:")
        print(f"  - 최종 수익률: {perf.get('total_return', 0) * 100:.2f}%")
        print(f"  - 연환산 수익률: {perf.get('annualized_return', 0) * 100:.2f}%")
        print(f"  - 변동성: {perf.get('volatility', 0) * 100:.2f}%")
        print(f"  - 샤프 지수: {perf.get('sharpe_ratio', 0):.2f}")
        print(f"  - 최대 낙폭(MDD): {perf.get('max_drawdown', 0) * 100:.2f}%")
        print(f"\n총 {len(result.get('transactions', []))} 건의 거래가 발생했습니다.")

except Exception as e:
    print(f"\n결과를 가져오는 중 오류가 발생했습니다: {e}")
    print(f"작업 상태: {task.status}")
