FROM redis:latest
RUN apt-get update && apt-get install -y python3 pip git && \
    pip3 install redis-py flask channels && \
    git clone https://github.com/luin/redis-ui.git /app
EXPOSE 9001
WORKDIR /app
CMD ["python3", "-m", "http.server", "9001"]
