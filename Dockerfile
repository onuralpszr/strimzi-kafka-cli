FROM python:3-alpine
USER root
RUN adduser -D kfkuser
RUN pip install strimzi-kafka-cli==0.1.0a68
USER kfkuser
RUN kfk --version