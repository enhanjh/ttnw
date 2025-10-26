
import time
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가합니다.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from workers.tasks import run_backtest_task
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# 백테스트할 펀더멘털 전략의 파라미터를 정의합니다.
strategy_params = {
    'fundamental_data_region': 'KR',
    'ranking_metric': 'market_cap', # 현재는 구현되지 않음, EPS > 0 조건만 사용됨
    'top_n': 5,
    're_evaluation_frequency': 'quarterly'
}

print("펀더멘털 지표 전략 백테스트 작업을 Celery 워커에게 요청합니다...")
task = run_backtest_task.delay(
    strategy_name='FundamentalIndicatorStrategy',
    strategy_params=strategy_params,
    start_date='2022-01-01', 
    end_date='2022-12-31'
)

print(f"작업이 성공적으로 전달되었습니다. Task ID: {task.id}")
print("결과를 기다리는 중... (최대 300초)")

try:
    # 이 테스트는 많은 데이터를 처리하므로 타임아웃을 길게 설정합니다.
    result = task.get(timeout=300)

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
