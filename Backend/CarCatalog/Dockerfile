FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends blender && rm -rf /var/lib/apt/lists/* && useradd -m catalog
WORKDIR /app
COPY server.py convert.py render_preview.py wheel_repair.py admin.html ./
COPY static ./static
RUN mkdir /data && chown catalog:catalog /data
USER catalog
VOLUME /data
EXPOSE 8787
CMD ["python", "server.py", "--host", "0.0.0.0", "--data", "/data", "--blender", "blender"]
