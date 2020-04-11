# https://github.com/SvanBoxel/gitlab-mirror-and-ci-action/blob/master/Dockerfile
FROM makocchi/alpine-git-curl-jq:latest

COPY entrypoint.sh /entrypoint.sh
COPY cred-helper.sh /cred-helper.sh

ENTRYPOINT ["/entrypoint.sh"]
