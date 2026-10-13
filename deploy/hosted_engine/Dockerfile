# BioScout hosted OpenSim engine -- the server behind Simulate on
# https://basgoncalves.github.io/bioscout-web/?lab=1
# Built by Hugging Face Spaces (sdk: docker) or any Docker host.
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libgfortran5 liblapack3 libblas3 \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir opensim==4.6 numpy pandas scipy matplotlib pyyaml packaging lxml c3d

# Hugging Face runs the container as uid 1000.
RUN useradd -m -u 1000 bs
WORKDIR /app
COPY --chown=bs bioscout ./bioscout
COPY --chown=bs example_data/orthoload ./example_data/orthoload
USER bs
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1 HOME=/home/bs \
    BIOSCOUT_HOST=0.0.0.0 PORT=7860
EXPOSE 7860
# BIOSCOUT_CODE is set as a Space variable and must match data/opensim/engine.json
# in bioscout-web. Uploaded trials are deleted after 6 h.
CMD ["python", "-m", "bioscout.lab.web_engine", "--work", "/tmp/bioscout_engine", "--keep-hours", "6"]
