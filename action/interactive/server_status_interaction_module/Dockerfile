FROM python:3.12-slim
WORKDIR /app
COPY libs/flask_core /app/libs/flask_core
RUN cd /app/libs/flask_core && pip install --no-cache-dir .
COPY action/interactive/server_status_interaction_module/requirements.txt /app/
COPY action/interactive/server_status_interaction_module /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /var/log/waddlebotlog
RUN groupadd -r waddlebot && useradd -r -g waddlebot -m waddlebot
RUN chown -R waddlebot:waddlebot /app /var/log/waddlebotlog
CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8097", "--workers", "4"]
