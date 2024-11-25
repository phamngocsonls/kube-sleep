FROM python:3.12.7-alpine3.20

ADD requirements.txt ./

RUN pip install -r requirements.txt

RUN rm -f ./requirements.txt

WORKDIR /

COPY main.py .

CMD ["python","-u","main.py"]