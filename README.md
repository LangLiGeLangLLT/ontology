```bash
python -m venv .venv
.venv\Scripts\activate
```

```python
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

model = ChatOpenAI(
    model=os.getenv("LLM_MODEL_ID"),
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL"),
    temperature=0,
)
```

```bash
python -m ecommerce.main
python -m ecommerce.main --demo

python -m ecommerce.customer_order_inference
python -m ecommerce.customer_order_inference --demo

python -m ecommerce.customer_order_tbox_reasoning --show-all
```

```bash
python -m edu.edu_onto
python -m edu.edu_infer
python -m edu.edu_owlready

# 不提供实例数据时：只构建教育领域模式并推理类层次
python -m edu.edu_owlready

# 数据暂时不可获取时，用最小演示实例验证个体级推理
python -m edu.edu_owlready --demo

python -m edu.edu_owl
```

```bash
python -m ecom.main
python -m ecom.build
python -m ecom.query
python -m ecom.test
```
