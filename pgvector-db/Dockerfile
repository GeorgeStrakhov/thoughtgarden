# Use the official PostgreSQL image as a parent image
FROM postgres:16 as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    postgresql-server-dev-$PG_MAJOR \
    wget

# Clone the specific version of pgvector and build it
ARG PGVECTOR_VERSION=v0.6.2
RUN git clone --branch $PGVECTOR_VERSION https://github.com/pgvector/pgvector.git
WORKDIR /pgvector
RUN make && make install

# Create the "postgres" role with a default password
RUN echo "CREATE ROLE postgres WITH SUPERUSER LOGIN PASSWORD 'postgres';" > /docker-entrypoint-initdb.d/init-role.sql

# Create a new image to keep it clean
FROM postgres:16
COPY --from=builder /usr/lib/postgresql/$PG_MAJOR/lib/vector.so /usr/lib/postgresql/$PG_MAJOR/lib/
COPY --from=builder /usr/share/postgresql/$PG_MAJOR/extension/vector* /usr/share/postgresql/$PG_MAJOR/extension/

# Set the shared_preload_libraries to include pgvector
RUN echo "shared_preload_libraries = 'vector'" >> /usr/share/postgresql/postgresql.conf.sample
