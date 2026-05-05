# MLFLOW SERVER FOR THE GUARDIAN SENTIMENT ANALYSIS PROJECT
FROM ghcr.io/mlflow/mlflow:v3.11.1

# HF Spaces requirement
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app
COPY --chown=user requirements.txt .
RUN python3.10 -m pip install --upgrade pip
RUN pip install --user --no-cache-dir -r requirements.txt

# Create MLFLOW schema in DB
COPY --chown=user create_schema.py .
RUN chmod +x create_schema.py

COPY --chown=user start.sh .
RUN chmod +x start.sh

EXPOSE 7860

CMD ["./start.sh"]



#CMD mlflow server \
#    --backend-store-uri $BACKEND_STORE_URI \
#    --artifacts-destination $ARTIFACT_ROOT \
#    --host 0.0.0.0 \
#    --port $PORT \
#    --disable-security-middleware