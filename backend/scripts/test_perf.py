import time
from app.services.validation_runner import runner
import asyncio

async def test_performance():
    loop = asyncio.get_event_loop()
    runner.start_session('C:\\Users\\Harshal\\Downloads\\videoplayback.mp4', loop)
    time.sleep(10)
    runner.stop_session()
    
    print('Evidence Generated:', runner.stats['evidence_captured'])
    print('Frames Processed:', runner.stats['frames_processed'])
    
    # Calculate avg raw metrics
    for k, v in runner.raw_metrics.items():
        if len(v) > 0:
            avg = sum(v) / len(v)
            print(f'{k}: avg {avg:.2f} ms')
        
asyncio.run(test_performance())
