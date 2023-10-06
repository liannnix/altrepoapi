FROM alt:p10

# set version label
ARG UID=1000
ARG GID=1000

ENV UNAME=api
ENV APP_HOME=/home/$UNAME/app

RUN \
    # fix Apt source lists
    rm -f /etc/apt/sources.list.d/*.list \
    && echo "rpm [p10] http://ftp.altlinux.org/pub/distributions/ALTLinux p10/branch/x86_64 classic" > /etc/apt/sources.list.d/alt.list \
    && echo "rpm [p10] http://ftp.altlinux.org/pub/distributions/ALTLinux p10/branch/noarch classic" >> /etc/apt/sources.list.d/alt.list \
    # installing packages
    && apt-get update \
    && yes | apt-get dist-upgrade \
    && yes | apt-get install \
        python3-module-flask \
        python3-module-flask-restx \
        python3-module-mmh3 \
        python3-module-clickhouse-driver \
        python3-module-gunicorn \
        python3-module-packaging \
        python3-module-ldap \
        python3-module-jwt \
        python3-module-redis-py \
        python3-module-flask-cors \
        tzdata \
    # clean-up Apt caches
    && rm -f /var/cache/apt/archives/*.rpm \
        /var/cache/apt/*.bin \
        /var/lib/apt/lists/*.* \
    # create user and directories
    && groupadd -g $GID -o $UNAME \
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

RUN touch /config/api.conf
