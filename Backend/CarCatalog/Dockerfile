FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends blender python3-numpy && rm -rf /var/lib/apt/lists/* && useradd -m catalog
# Debian Blender uses the system Python, not the image's /usr/local Python.
# Verify the FBX dependency inside Blender itself; fail the build if missing.
RUN blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python-expr "import numpy; print('BLENDER_NUMPY_OK', numpy.__version__)"
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py matchmaking.py realtime.py convert.py render_preview.py wheel_repair.py admin.html ./
COPY static ./static
RUN mkdir /data && chown catalog:catalog /data
USER catalog
VOLUME /data
EXPOSE 8787
CMD ["python", "server.py", "--host", "0.0.0.0", "--data", "/data", "--blender", "blender"]
