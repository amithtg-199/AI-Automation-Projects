FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Install uv securely
RUN pip install uv

# Set workdir
WORKDIR /sandbox

# Copy pyproject.toml / requirements to bake in deps
COPY pyproject.toml .

# Install dependencies statically
RUN uv sync --frozen

# The command to run is provided dynamically at replay time.
# But we ensure it drops privileges if needed, or we just run as pwuser.
USER pwuser
