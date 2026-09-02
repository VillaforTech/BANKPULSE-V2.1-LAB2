FROM mcr.microsoft.com/devcontainers/java:1-21-bookworm

# Codespaces fix: the inherited Yarn APT source can fail during feature installation.
# Removing it before Dev Container features run keeps apt update/build reproducible.
RUN rm -f /etc/apt/sources.list.d/yarn.list
