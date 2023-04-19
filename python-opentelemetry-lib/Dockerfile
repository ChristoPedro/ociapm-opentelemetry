FROM python:3.8-slim as dependency
WORKDIR /reqs
COPY requirements.txt /reqs
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.8-slim
WORKDIR /home/app
COPY func.py .
COPY --from=dependency /usr/local/lib/python3.8/site-packages/ /usr/local/lib/python3.8/site-packages/
ENV COLLECTOR-ENDPOINT=http://simplest-collector.default:4317
RUN useradd --uid 10000 runner
USER 10000
CMD ["python","./func.py"]
EXPOSE 5000