FROM alt:p10

# set version label
ARG UID=1000
ARG GID=1000

ENV UNAME=api
ENV APP_HOME=/home/$UNAME/app

# TODO: remove packages from task #291581 
# after approval for p10 branch
RUN apt-get update \
    && yes | apt-get install apt-repo \
    && apt-repo add 291581 \
    && apt-get update \
    && yes | apt-get install \
    python3-module-flask \
    python3-module-flask-restx \
    python3-module-rpm \
    python3-module-mmh3 \
    python3-module-clickhouse-driver \
    python3-module-gunicorn

RUN groupadd -g $GID -o $UNAME \
    && useradd -m -u $UID -g $GID -o -s /bin/bash $UNAME \
    && mkdir -p /config && mkdir -p /log \
    && chown -R $UID:$GID /config \
    && chown -R $UID:$GID /log \
    && mkdir $APP_HOME

WORKDIR $APP_HOME

COPY . $APP_HOME

RUN chown -R $UID:$GID $APP_HOME

USER $UNAME

RUN cp $APP_HOME/bin/altrepo-api run-api

ADD api.conf.docker /config/api.conf
