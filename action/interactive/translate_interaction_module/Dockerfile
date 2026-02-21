FROM python:3.12-slim

WORKDIR /app

# Install shared flask_core library
COPY libs/flask_core /app/libs/flask_core
RUN cd /app/libs/flask_core && pip install --no-cache-dir .

# Install dependencies
COPY action/interactive/translate_interaction_module/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy module source
COPY action/interactive/translate_interaction_module /app/

# Generate gRPC stubs at build time
# Use -I . so protoc sees proto/ as a package prefix, generating
# 'from proto import translate_interaction_pb2' (not bare import)
RUN python -m grpc_tools.protoc \
    -I . \
    --python_out=. \
    --grpc_python_out=. \
    proto/translate_interaction.proto

# Non-root user
RUN mkdir -p /var/log/waddlebotlog && \
    groupadd -r waddlebot && useradd -r -g waddlebot -m waddlebot && \
    chown -R waddlebot:waddlebot /app /var/log/waddlebotlog

USER waddlebot

EXPOSE 8033 50033

CMD ["python", "app.py"]
