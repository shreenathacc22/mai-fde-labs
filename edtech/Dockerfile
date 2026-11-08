# Northfield Help Desk as one container — lab 2b's Dockerfile, pointed at the edtech product.
# Build from the REPO ROOT (the product reuses labs/):
#
#   docker build -f edtech/Dockerfile -t northfield-desk .
#   docker run --rm -p 7867:7867 \
#     -e OPENAI_API_KEY=<your key> \
#     -e OPENAI_BASE_URL=https://learn.modernaipro.com/api/llm/v1 \
#     -e CHAT_SECRET=$(openssl rand -hex 24) \
#     -e CAMPUS_USER=tutor.lena \
#     northfield-desk
#
# Open http://127.0.0.1:7867/?k=<CHAT_SECRET>   (dashboard: /dashboard)
# CAMPUS_USER is who the container acts as. Deploy as the least user that does the job:
# a student-facing desk runs as that student's identity (in a real product, per-login SSO),
# never as registrar.ana. Keys come from the environment; nothing secret is in the image.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt requirements-graph.txt ./
RUN pip install --no-cache-dir -r requirements-graph.txt
COPY labs/ labs/
COPY edtech/ edtech/
ENV MAI_CLASSIFY=0 MAI_TRACE=0 CAMPUS_STATE_DIR=/tmp/campus CAMPUS_USER=tutor.lena
EXPOSE 7867
CMD ["python", "edtech/app.py", "--web", "--host", "0.0.0.0", "--port", "7867"]
