FROM public.ecr.aws/lambda/python:3.12

# Install dependencies - FastAPI + Mangum for Lambda, GraphRAG toolkit
RUN pip install --no-cache-dir \
    https://github.com/awslabs/graphrag-toolkit/archive/refs/tags/v3.15.0.zip#subdirectory=lexical-graph \
    boto3 \
    opensearch-py \
    fastapi \
    mangum && \
    pip install --no-cache-dir --no-deps llama-index-vector-stores-opensearch

COPY handler.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.handler"]
