from evalscope.run import run_task
from evalscope.config import TaskConfig

cfg = TaskConfig(
    model="deepseek-flash",
    api_url="https://api.deepseek.com/v1",
    api_key="sk-3058833f2c3b4322ab1a59feb3c542dc",
    eval_type="openai_api",
    datasets=["gsm8k"],
    eval_batch_size=1,
    limit=10,
)
run_task(cfg)

