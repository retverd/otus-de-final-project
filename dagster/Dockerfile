ARG DAGSTER_BASE_IMG=latest
FROM python:$DAGSTER_BASE_IMG

ARG DAGSTER_HOME

RUN mkdir -p $DAGSTER_HOME
WORKDIR $DAGSTER_HOME

COPY ./dagster/dagster.yaml ./dagster/workspace.yaml ./dagster/requirements.txt ./

RUN pip install -r requirements.txt

ENTRYPOINT ["dagster","dev","-h","0.0.0.0","-p","3000","-m","payload"]