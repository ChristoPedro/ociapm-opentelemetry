FROM python:3.11 as dependency
WORKDIR /reqs
COPY requirements.txt /reqs
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11
WORKDIR /home/app
COPY funcsemotl.py .
COPY --from=dependency /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
CMD ["python","./funcsemotl.py"]
EXPOSE 5000