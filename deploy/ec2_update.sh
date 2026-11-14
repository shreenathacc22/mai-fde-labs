#!/usr/bin/env bash
# Lab 2b's chat on the EC2 instance from the weekend (Name=fde-lab2b-poc): roll it to the current commit.
#
#   deploy/ec2_update.sh push       build linux/amd64 from the current commit, push to ECR as fde-chat:<commit>
#   deploy/ec2_update.sh roll       pull on the instance and swap the container; smoke; roll back on failure
#   deploy/ec2_update.sh smoke      page 200 · API 401 without / with a wrong secret · one real turn with it
#   deploy/ec2_update.sh status     what is running on the instance (names, images, uptime — never the environment)
#   deploy/ec2_update.sh rollback   put back the container that `roll` replaced (kept stopped as fde-chat-prev)
#
# Why EC2 and not App Runner: App Runner refuses new services on accounts that have
# not used it ("Account … can't create new App Runner services", 2026-11-14).
#
# How secrets travel (nothing is printed, put on a command line, baked into the image or committed):
#   - OPENAI_API_KEY comes from mai-fde-labs/.env and goes over SSH stdin into a mode-600 env file on the
#     instance, which is deleted once the container is created; it is also stored in Secrets Manager
#     (fde-lab2b/openai-api-key) as the record of what is deployed.
#   - CHAT_SECRET, OPENAI_BASE_URL and ESTATE_USER are carried over from the running container on the
#     instance itself, so links and the local copy (~/.ssh/fde-lab2b.chat_secret) keep working.
#   - The ECR login is a 12-hour token sent over SSH stdin; the instance logs out after the pull.
# Network: the security group admits 22/7866/7867 from one /32 only (the operator's address); there is no TLS,
# so the secret header is only ever sent from that address.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
NAME_TAG="${NAME_TAG:-fde-lab2b-poc}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/fde-lab2b.pem}"
SECRET_FILE="${SECRET_FILE:-$HOME/.ssh/fde-lab2b.chat_secret}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="$(git -C "$ROOT" rev-parse --short HEAD)"
PORT=7866

aws_() { aws --region "$REGION" "$@"; }
mask() { sed -E 's/[0-9]{12}/<account>/g'; }
host() { aws_ ec2 describe-instances --filters "Name=tag:Name,Values=$NAME_TAG" Name=instance-state-name,Values=running \
          --query 'Reservations[0].Instances[0].PublicIpAddress' --output text; }
on() { ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 -o LogLevel=ERROR "ec2-user@$(host)" "$@"; }
uri() { echo "$(aws_ sts get-caller-identity --query Account --output text).dkr.ecr.$REGION.amazonaws.com/fde-chat"; }

push() {
  if [ -n "$(git -C "$ROOT" status --porcelain -- labs estate requirements*.txt Dockerfile)" ]; then
    echo "uncommitted changes under labs/ estate/ or the Dockerfile: commit first, so the tag names the code"; exit 1
  fi
  local U; U="$(uri)"
  aws_ ecr get-login-password | docker login --username AWS --password-stdin "${U%/*}" >/dev/null
  docker build --platform linux/amd64 -t "$U:$TAG" "$ROOT" 2>&1 | grep -E '^#[0-9]+ (DONE|naming|writing)|ERROR' | mask || true
  docker push "$U:$TAG" 2>&1 | tail -1 | mask
  echo "pushed fde-chat:$TAG"
}

roll() {
  local U; U="$(uri)"
  echo "instance: $NAME_TAG ($(host)) · image fde-chat:$TAG"
  aws_ ecr get-login-password | on "docker login --username AWS --password-stdin ${U%/*} >/dev/null && docker pull -q $U:$TAG && docker logout ${U%/*} >/dev/null" | mask
  # the key: local .env -> stdin -> a 600 file on the instance; the other values from the running container
  ( set +u; set -a; . "$ROOT/.env"; set +a; printf 'OPENAI_API_KEY=%s\n' "$OPENAI_API_KEY" ) | on "set -e; umask 077; f=~/.fde-chat.env; trap 'shred -u \$f 2>/dev/null || rm -f \$f' EXIT
    cat > \$f
    docker inspect fde-chat --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E '^(CHAT_SECRET|OPENAI_BASE_URL|ESTATE_USER)=' >> \$f
    test \$(grep -cE '^(OPENAI_API_KEY|CHAT_SECRET|OPENAI_BASE_URL|ESTATE_USER)=' \$f) -eq 4 || { echo 'env incomplete: nothing changed'; exit 1; }
    docker rm -f fde-chat-prev >/dev/null 2>&1 || true
    docker stop fde-chat >/dev/null
    docker rename fde-chat fde-chat-prev
    docker run -d --name fde-chat --restart unless-stopped -p $PORT:$PORT --env-file \$f $U:$TAG >/dev/null"
  echo "container swapped; previous one kept stopped as fde-chat-prev"
  for _ in $(seq 1 30); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' -m 5 "http://$(host):$PORT/")" = 200 ] && break; sleep 2
  done
  if smoke; then
    ( set +u; set -a; . "$ROOT/.env"; set +a; t="$(mktemp)"; chmod 600 "$t"; printf '%s' "$OPENAI_API_KEY" > "$t"
      aws_ secretsmanager put-secret-value --secret-id fde-lab2b/openai-api-key --secret-string "file://$t" >/dev/null; rm -f "$t" )
    echo "Secrets Manager fde-lab2b/openai-api-key: updated to the deployed key (value not shown)"
  else
    echo "smoke failed: rolling back"; rollback; exit 1
  fi
}

smoke() {
  local H S body ok=0 h out
  H="http://$(host):$PORT"; S="$(tr -d '\n' < "$SECRET_FILE")"
  h="$(mktemp)"; chmod 600 "$h"; printf 'X-Chat-Secret: %s\n' "$S" > "$h"; unset S
  body='{"thread":"smoke","text":"In one sentence: which user are you acting as, and which regions can you see?"}'
  local page nos wrong
  page="$(curl -s -o /dev/null -w '%{http_code}' -m 10 "$H/")"
  nos="$(curl -s -o /dev/null -w '%{http_code}' -m 10 -X POST -H 'Content-Type: application/json' -d "$body" "$H/api/chat")"
  wrong="$(curl -s -o /dev/null -w '%{http_code}' -m 10 -X POST -H 'X-Chat-Secret: wrong' -H 'Content-Type: application/json' -d "$body" "$H/api/chat")"
  out="$(curl -s -m 180 -w '\nHTTP %{http_code}' -X POST -H @"$h" -H 'Content-Type: application/json' -d "$body" "$H/api/chat")"; rm -f "$h"
  echo "page                : $page"
  echo "API, no secret      : $nos"
  echo "API, wrong secret   : $wrong"
  echo "API, right secret   : $(echo "$out" | tail -1)"
  echo "$out" | sed '$d' | python3 -c 'import sys,json
try: d=json.load(sys.stdin)
except Exception: print("  reply: (not JSON)"); sys.exit()
ms=[m for m in d.get("messages") or [] if m.get("text")]
r=ms[-1]["text"] if ms else json.dumps(d, ensure_ascii=False)
print("  reply:", " ".join(str(r).split())[:300])'
  [ "$page" = 200 ] && [ "$nos" = 401 ] && [ "$wrong" = 401 ] && echo "$out" | tail -1 | grep -q 'HTTP 200' || ok=1
  return $ok
}

status() {
  echo "instance: $NAME_TAG ($(host))"
  on 'docker ps -a --format "{{.Names}} | {{.Image}} | {{.Status}} | {{.Ports}}"' | mask
}

rollback() {
  on "docker inspect fde-chat-prev >/dev/null 2>&1 || { echo 'nothing to roll back to'; exit 1; };
      docker rm -f fde-chat >/dev/null 2>&1; docker rename fde-chat-prev fde-chat && docker start fde-chat >/dev/null && echo 'rolled back'"
}

case "${1:-}" in
  push) push ;; roll) roll ;; smoke) smoke ;; status) status ;; rollback) rollback ;;
  *) sed -n '2,9p' "$0"; exit 2 ;;
esac
