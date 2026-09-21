FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock.txt requirements-toy.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
ARG WITH_TOY=0
RUN if [ "$WITH_TOY" = "1" ]; then pip install --no-cache-dir -r requirements-toy.txt; fi
COPY . .
ENV PYTHONHASHSEED=0 MPLBACKEND=Agg
CMD ["python", "-m", "experiments.reproduce"]
