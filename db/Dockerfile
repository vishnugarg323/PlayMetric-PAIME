FROM postgres:15-alpine

ENV POSTGRES_USER=paime
ENV POSTGRES_PASSWORD=paime123
ENV POSTGRES_DB=paime

COPY init.sql /docker-entrypoint-initdb.d/

EXPOSE 5432