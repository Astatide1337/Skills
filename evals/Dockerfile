FROM node:22-bookworm-slim
ARG CLAUDE_CODE_VERSION=2.1.322
RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends git python3 ca-certificates ripgrep >/dev/null \
 && rm -rf /var/lib/apt/lists/* \
 && ln -s /usr/bin/python3 /usr/local/bin/python \
 && npm install -g --silent "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"
USER node
RUN git config --global user.name dev && git config --global user.email dev@example.com \
 && git config --global init.defaultBranch main
WORKDIR /home/node
